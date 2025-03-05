import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple

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

    async def handle_call_score(self, code: int, packet: Dict[str, Any]):
        """处理叫分请求
        
        重写Player类的handle_call_score方法，使用LLM进行决策。
        
        Args:
            code: 请求代码
            packet: 请求数据包
        """
        logger.info(f"LLM玩家[{self.uid}]处理叫分请求: code={code}, packet={packet}")
        if code == Pt.REQ_CALL_SCORE:            
            history_calls = [] # 历史叫分记录
            for player in self.room.players:
                if player.rob != -1:
                    history_calls.append((player.seat, player.rob))
            
            logger.info(f"LLM玩家[{self.uid}]历史叫分记录: {history_calls}")
            
            try:
                logger.info(f"LLM玩家[{self.uid}]开始决策是否叫地主...")
                decision = self.card_player.decide_call_landlord(
                    self.hand_pokers,
                    history_calls
                )
                
                logger.info(f"LLM玩家[{self.uid}]决策结果: {decision}")
                                
                # 设置叫分结果
                self.rob = decision
                
                is_end = self.room.on_rob(self)
                
                if is_end:
                    logger.info(f"LLM玩家[{self.uid}]叫分结束，切换状态到PLAYING")
                    self.change_state(State.PLAYING)  # 
                    logger.info(f'ROB END LANDLORD[{self.room.landlord}]')
                    
                    # 检查是否是地主
                    landlord = self.room.landlord
                    if landlord and landlord.uid == self.uid:
                        logger.info(f"LLM玩家[{self.uid}]成为地主")
                        if self.room.pokers and len(self.room.pokers) > 0:
                            logger.info(f"LLM玩家[{self.uid}]获得底牌: {self.room.pokers}")
                            logger.info(f"LLM玩家[{self.uid}]当前手牌: {self._hand_pokers}, 牌数: {len(self._hand_pokers)}")
                
                # 广播叫分结果
                response = [Pt.RSP_CALL_SCORE, {
                    'uid': self.uid,
                    'rob': self.rob,
                    'landlord': -1,  # 默认为-1，表示叫分未结束
                }]
                
                # 如果叫分结束，添加地主信息
                if is_end:
                    landlord_uid = self.room.landlord.uid if self.room.landlord else -1
                    landlord_pokers = self.room.pokers
                    response[1]['landlord'] = landlord_uid
                    response[1]['pokers'] = landlord_pokers
                    response[1]['multiple'] = self.room.multiple
                    logger.info(f"LLM玩家[{self.uid}]广播叫分结束消息，地主: {landlord_uid}, 底牌: {landlord_pokers}")
                
                self.room.broadcast(response)
                
            except CardDecisionError as e:
                logger.error(f"LLM玩家[{self.uid}]决策出错: {e}")
                # 默认不叫地主
                self.rob = 0
                logger.info(f"LLM玩家[{self.uid}]默认不叫地主")
                
                # 处理叫分结果
                is_end = self.room.on_rob(self)
                
                # 广播叫分结果
                response = [Pt.RSP_CALL_SCORE, {
                    'uid': self.uid,
                    'rob': self.rob,
                    'landlord': -1,  # 默认为-1，表示叫分未结束
                }]
                
                # 如果叫分结束，添加地主信息
                if is_end:
                    landlord_uid = self.room.landlord.uid if self.room.landlord else -1
                    landlord_pokers = self.room.pokers
                    response[1]['landlord'] = landlord_uid
                    response[1]['pokers'] = landlord_pokers
                    response[1]['multiple'] = self.room.multiple
                
                self.room.broadcast(response)
        else:
            logger.info(f"LLM玩家[{self.uid}]调用父类处理叫分请求")
            await super().handle_call_score(code, packet)
    
    async def handle_playing(self, code: int, packet: Dict[str, Any]):
        """处理出牌请求
        
        重写Player类的handle_playing方法，使用LLM进行决策。
        
        Args:
            code: 请求代码
            packet: 请求数据包
        """
        if code == Pt.REQ_SHOT_POKER:
            try:
                # 获取上家出牌信息
                last_player_position = self.room.last_shot_seat
                last_played_cards = self.room.last_shot_poker if self.room.last_shot_seat != self.seat else []
                
                # 使用LLM决策出牌
                decision = self.card_player.decide_play_cards(
                    self.hand_pokers,
                    last_played_cards,
                    last_player_position,
                    self.seat,
                    self.landlord == 1,
                    is_follow=len(last_played_cards) > 0  # 如果上家有出牌，则为跟牌
                )
                
                # 模拟思考时间
                await asyncio.sleep(self.decision_delay)
                
                # 验证出牌合法性
                if decision and not rule.is_contains(self._hand_pokers, decision):
                    logger.warning(f"LLM玩家[{self.uid}]出牌不合法: {decision}")
                    decision = []
                
                # 处理出牌
                if decision:
                    error = self.room.on_shot(self.seat, decision)
                    if error:
                        logger.warning(f"LLM玩家[{self.uid}]出牌错误: {error}")
                        # 出错时默认不出
                        decision = []
                
                # 如果决定不出或出牌不合法，则不出
                if not decision:
                    self.room.broadcast([Pt.RSP_SHOT_POKER, {'uid': self.uid, 'pokers': [], 'multiple': self.room.multiple}])
                    self.room.go_next_turn()
                    return
                
                # 从手牌中移除出的牌
                for p in decision:
                    self._hand_pokers.remove(p)
                
                # 广播出牌结果
                self.room.broadcast([Pt.RSP_SHOT_POKER, {'uid': self.uid, 'pokers': decision, 'multiple': self.room.multiple}])
                logger.info(f'LLM玩家[{self.uid}]出牌: {decision}')
                
                # 检查是否出完牌
                if self._hand_pokers:
                    self.room.go_next_turn()
                else:
                    self.change_state(4)  # State.GAME_OVER
                    self.room.on_game_over(self)
                    await self.room.save_shot_round()
                
            except CardDecisionError as e:
                logger.error(f"LLM玩家[{self.uid}]出牌决策错误: {e}")
                # 出错时使用规则引擎的最佳出牌
                if not self.room.last_shot_poker or self.room.last_shot_seat == self.seat:
                    best_shot = rule.find_best_shot(self.hand_pokers)
                    await super().handle_playing(code, {'pokers': best_shot})
                else:
                    await super().handle_playing(code, {'pokers': []})
        else:
            await super().handle_playing(code, packet)
    
    def on_timeout(self):
        """处理超时事件
        
        重写Player类的on_timeout方法，使用LLM进行决策。
        """
        # LLM玩家不应该超时，但如果发生了，使用规则引擎的决策
        super().on_timeout()
        

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