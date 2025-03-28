import logging
from typing import List, Dict, Any, Optional, Tuple
from tornado.ioloop import IOLoop

# from server.api.game.player import Player
from server.api.game.components.simple import RobotPlayer
from server.api.game.protocol import Protocol as Pt
from server.api.game.rule import rule

from .cardplayer import LLMCardPlayer, CardDecisionError
from .openaiclient import OpenAIClient

logger = logging.getLogger(__name__)

class LLMPlayer(RobotPlayer):
    """使用LLM进行决策的斗地主AI玩家
    
    该类继承自服务器端的RobotPlayer类，并使用LLMCardPlayer进行决策。
    
    Attributes:
        card_player: LLM卡牌玩家实例
        decision_delay: 决策延迟时间（秒）
    """
    
    def __init__(
        self, 
        uid: int, 
        name: str, 
        client: OpenAIClient,
        system_prompt: str = "",
        decision_delay: float = 0.1,
        **kwargs
    ):
        """初始化LLM玩家
        
        Args:
            uid: 玩家ID
            name: 玩家名称
            client: OpenAI客户端
            system_prompt: 系统提示词
            decision_delay: 决策延迟时间（秒）
        """
        super().__init__(uid, name, None)
        self.card_player = LLMCardPlayer(client, system_prompt)
        self.decision_delay = decision_delay
        
        # 调试信息
        self.debug_info = {
            "landlord_set": False,
            "bottom_cards_added": False,
            "bottom_cards": [],
            "hand_before_bottom": [],
            "hand_after_bottom": []
        }

    def restart(self):
        self.card_player.reset()
        return super().restart()

    def auto_rob(self):
        """重写auto_rob方法，使用LLM进行叫分决策"""
        try:
            # 获取历史叫分记录
            history_calls = []
            for player in self.room.players:
                if player.rob != -1:
                    history_calls.append((player.seat, player.rob))
            
            # logger.info(f"LLM玩家[{self.uid}]历史叫分记录: {history_calls}")
            logger.info(f"LLM玩家[{self.uid}]手牌: {self.hand_pokers}")
            
            # 使用LLM决策是否叫地主
            decision = self.card_player.decide_call_landlord(
                self.hand_pokers,
                history_calls
            )
            logger.info(f"LLM玩家[{self.uid}]决策结果: {decision}")
            
            # 发送叫分请求
            IOLoop.current().call_later(self.decision_delay, self.to_server, Pt.REQ_CALL_SCORE, {'rob': decision})
            
        except CardDecisionError as e:
            logger.error(f"LLM玩家[{self.uid}]决策出错: {e}")
            # 出错时调用父类的auto_rob作为后备方案
            super().auto_rob()

    def auto_shot(self):
        """重写auto_shot方法，使用LLM进行出牌决策"""
        try:
            # 获取上家出牌信息
            last_player_position = self.room.last_shot_seat
            last_played_cards = self.room.last_shot_poker if self.room.last_shot_seat != self.seat else []
            is_follow = len(last_played_cards) > 0  # 是否是跟牌
            
            logger.info(f"LLM玩家[{self.uid}]决策出牌...")
            
            last_player_is_landlord = self.room.players[last_player_position].landlord == 1
            # 使用LLM决策出牌
            decision = self.card_player.decide_play_cards(
                self.hand_pokers,
                last_played_cards,
                last_player_position,
                last_player_is_landlord,
                self.seat,
                self.landlord == 1,
                is_follow=is_follow
            )
            
            logger.info(f"LLM玩家[{self.uid}]决策结果: {decision}")
            
            # 验证出牌合法性（检查手牌中是否有这些牌）
            if decision and not rule.is_contains(self._hand_pokers, decision):
                logger.warning(f"LLM玩家[{self.uid}]出牌不合法: {decision}")
                decision = []
            
            # 如果是跟牌，验证出牌是否符合规则（是否大于上家出牌）
            if decision and is_follow:
                # 获取出牌类型
                decision_cards = rule._to_cards(decision)
                last_cards = rule._to_cards(last_played_cards)
                
                # 检查牌型是否相同
                decision_type, _ = rule._get_cards_value(decision_cards)
                last_type, _ = rule._get_cards_value(last_cards)
                
                # 比较牌的大小
                compare_result = rule.compare_pokers(decision, last_played_cards)
                
                # 如果牌型不同且不是炸弹或火箭，或者牌型相同但比上家小，则出牌无效
                if (decision_type != last_type and decision_type not in ['bomb', 'rocket']) or compare_result <= 0:
                    logger.warning(f"LLM玩家[{self.uid}]出牌不符合规则: {decision_type} vs {last_type}, 比较结果: {compare_result}")
                    decision = []
            
            # 如果是主动出牌，验证出牌是否符合规则（是否是有效的牌型）
            if decision and not is_follow:
                # 获取出牌类型
                decision_cards = rule._to_cards(decision)
                decision_type, _ = rule._get_cards_value(decision_cards)
                
                # 如果不是有效的牌型，则出牌无效
                if not decision_type:
                    logger.warning(f"LLM玩家[{self.uid}]出牌不是有效的牌型: {decision}")
                    decision = []
            
            # 如果是主动出牌且没有决策结果，使用父类的策略
            if not decision and not is_follow:
                logger.info(f"LLM玩家[{self.uid}]主动出牌决策为空或不合法，使用规则引擎出牌")
                super().auto_shot()
            # 如果是跟牌且没有决策结果，选择不出
            elif not decision and is_follow:
                logger.info(f"LLM玩家[{self.uid}]跟牌决策为空或不合法，选择不出")
                IOLoop.current().call_later(self.decision_delay, self.to_server, Pt.REQ_SHOT_POKER, {'pokers': []})
            else:
                # 发送出牌请求
                logger.info(f"LLM玩家[{self.uid}]发送出牌请求: {decision}")
                IOLoop.current().call_later(self.decision_delay, self.to_server, Pt.REQ_SHOT_POKER, {'pokers': decision})
            
        except CardDecisionError as e:
            logger.error(f"LLM玩家[{self.uid}]决策出错: {e}")
            # 出错时调用父类的auto_shot作为后备方案
            super().auto_shot()
    
    def on_timeout(self):
        """处理超时事件
        
        重写Player类的on_timeout方法，使用LLM进行决策。
        """
        # LLM玩家不应该超时，但如果发生了，使用规则引擎的决策
        super().on_timeout()
        
    def _write_message(self, packet):
        """处理服务器发送的消息
        
        重写父类的方法，添加对错误消息的处理。
        
        Args:
            packet: 消息包
        """
        code = packet[0]
        
        # 处理错误消息
        if code == Pt.ERROR:
            error_reason = packet[1].get('reason', '')
            logger.warning(f"LLM玩家[{self.uid}]收到错误消息: {error_reason}")
            
            # 如果是出牌相关的错误，且当前是自己的回合，尝试重新出牌
            if ('Poker' in error_reason or 'poker' in error_reason) and self.room.turn_player == self:
                logger.info(f"LLM玩家[{self.uid}]尝试重新出牌")
                # 如果是跟牌，选择不出
                if self.room.last_shot_seat != self.seat:
                    logger.info(f"LLM玩家[{self.uid}]选择不出牌")
                    IOLoop.current().call_later(self.decision_delay, self.to_server, Pt.REQ_SHOT_POKER, {'pokers': []})
                else:
                    # 如果是主动出牌，使用规则引擎出牌
                    logger.info(f"LLM玩家[{self.uid}]使用规则引擎出牌")
                    super().auto_shot()
            return
            
        # 调用父类的方法处理其他消息
        super()._write_message(packet)

# 创建LLM玩家的工厂函数
def create_llm_player(
    uid: int, 
    name: str, 
    api_key: str = "ollama",
    base_url: str = "http://localhost:11434/v1",
    model: str = "qwen2.5:32b",
    system_prompt: str = "",
    decision_delay: float = 1.0,
    **kwargs
) -> LLMPlayer:
    """创建LLM玩家
    
    Args:
        uid: 玩家ID
        name: 玩家名称
        api_key: API密钥
        base_url: API基础URL
        model: 模型名称
        system_prompt: 系统提示文本
        decision_delay: 决策延迟时间（秒）
        **kwargs: 其他参数
        
    Returns:
        LLMPlayer: LLM玩家实例
    """
    client = OpenAIClient(base_url, api_key, model, temperature=0.1)
    return LLMPlayer(uid, name, client, system_prompt, decision_delay, **kwargs)


# 测试代码
def test_llm_player():
    """测试LLM玩家功能"""
    # 创建LLM玩家
    player = create_llm_player(999, "LLM玩家")
    print(f"创建LLM玩家: {player}")
    
    # 这里只是创建了玩家实例，实际测试需要在游戏环境中进行
    # 可以通过修改server/api/game/globalvar.py中的代码，将LLM玩家集成到游戏中

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_llm_player() 