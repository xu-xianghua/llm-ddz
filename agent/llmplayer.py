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

    def auto_rob(self):
        """重写auto_rob方法，使用LLM进行叫分决策"""
        try:
            # 获取历史叫分记录
            history_calls = []
            for player in self.room.players:
                if player.rob != -1:
                    history_calls.append((player.seat, player.rob))
            
            logger.info(f"LLM玩家[{self.uid}]历史叫分记录: {history_calls}")
            logger.info(f"LLM玩家[{self.uid}]手牌: {self.hand_pokers}")
            
            # 使用LLM决策是否叫地主
            logger.info(f"LLM玩家[{self.uid}]开始决策是否叫地主...")
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
            # 获取当前游戏状态
            last_player_position = self.room.last_shot_seat
            last_played_cards = self.room.last_shot_poker if self.room.last_shot_seat != self.seat else []
            
            logger.info(f"LLM玩家[{self.uid}]开始决策出牌...")
            logger.info(f"当前手牌: {self.hand_pokers}")
            logger.info(f"上家出牌: {last_played_cards}")
            
            # 使用LLM决策出牌
            decision = self.card_player.decide_play_cards(
                self.hand_pokers,
                last_played_cards,
                last_player_position,
                self.seat,
                self.landlord == 1,
                is_follow=len(last_played_cards) > 0
            )
            
            logger.info(f"LLM玩家[{self.uid}]决策结果: {decision}")
            
            # 验证出牌合法性
            if decision and not rule.is_contains(self._hand_pokers, decision):
                logger.warning(f"LLM玩家[{self.uid}]出牌不合法: {decision}")
                decision = []
            
            # 发送出牌请求
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