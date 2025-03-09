import logging
import random
import json
import os
from typing import List, Dict, Any, Optional, Tuple
import time
from collections import Counter, defaultdict

from .cardplayer import LLMCardPlayer
from .openaiclient import OpenAIClient
from .idiotplayer import IdiotPlayer

logger = logging.getLogger(__name__)

class DDZGame:
    """斗地主游戏实现
    
    这个类实现了斗地主游戏的核心逻辑，包括发牌、抢地主、出牌等流程。
    游戏使用LLM模型作为玩家进行决策。
    
    Attributes:
        players: 三个玩家的列表
        bottom_cards: 底牌
        landlord_index: 地主玩家的索引
        current_player_index: 当前出牌玩家的索引
        last_played_cards: 上一次出的牌
        last_player_index: 上一次出牌的玩家索引
        game_over: 游戏是否结束
        winner_index: 获胜玩家的索引
    """
    
    def __init__(self, clients: List[OpenAIClient], system_prompts: List[str] = None, use_idiot_player: List[bool] = None):
        """初始化斗地主游戏
        
        Args:
            clients: 三个OpenAI客户端，用于创建LLM玩家
            system_prompts: 三个玩家的系统提示词，如果为None则使用默认提示词
            use_idiot_player: 是否使用简单AI玩家，如果为True则使用IdiotPlayer，否则使用LLMCardPlayer
        """
        if system_prompts is None:
            system_prompts = [""] * 3
        
        if use_idiot_player is None:
            use_idiot_player = [False, False, False]
        
        # 初始化三个玩家
        self.players = []
        for i in range(3):
            if use_idiot_player[i]:
                self.players.append(IdiotPlayer(f"玩家{i+1}"))
            else:
                self.players.append(LLMCardPlayer(clients[i], system_prompts[i]))
        
        # 初始化游戏状态
        self.bottom_cards = []
        self.landlord_index = -1
        self.current_player_index = 0
        self.last_played_cards = []
        self.last_player_index = -1
        self.game_over = False
        self.winner_index = -1
    
    def deal_cards(self):
        """发牌并分配给玩家"""
        # 生成一副完整的牌（54张）
        all_cards = list(range(1, 55))
        random.shuffle(all_cards)
        
        # 分配牌给三个玩家，每人17张，底牌3张
        for i in range(3):
            self.players[i].hand_cards = sorted(all_cards[i*17:(i+1)*17])
        
        self.bottom_cards = sorted(all_cards[51:])
        
        # 打印每个玩家的手牌
        for i, player in enumerate(self.players):
            logger.info(f"玩家{i+1}的手牌: {self._format_cards(player.hand_cards)}")
        
        logger.info(f"底牌: {self._format_cards(self.bottom_cards)}")
        
        # 随机选择第一个叫地主的玩家
        self.current_player_index = random.randint(0, 2)
        logger.info(f"玩家{self.current_player_index+1}先叫地主")
        
        return True
    
    def bid_for_landlord(self):
        """进行叫地主流程"""
        history_calls = []
        max_bid = 0
        max_bidder = -1
        
        # 每个玩家依次叫分
        for _ in range(3):
            player = self.players[self.current_player_index]
            
            # 使用LLM决策叫分
            bid = player.decide_call_landlord(player.hand_cards, history_calls)
            
            logger.info(f"玩家{self.current_player_index+1}叫分: {bid}")
            
            # 记录叫分历史
            history_calls.append((self.current_player_index, bid))
            
            # 更新最高叫分
            if bid > max_bid:
                max_bid = bid
                max_bidder = self.current_player_index
            
            # 如果已经叫3分，直接结束
            if bid == 3:
                break
            
            # 轮到下一个玩家
            self.current_player_index = (self.current_player_index + 1) % 3
        
        # 确定地主
        if max_bid > 0:
            self.landlord_index = max_bidder
            # 地主获得底牌
            self.players[self.landlord_index].hand_cards.extend(self.bottom_cards)
            self.players[self.landlord_index].hand_cards.sort()
            
            # 设置地主标志
            if hasattr(self.players[self.landlord_index], 'is_landlord'):
                self.players[self.landlord_index].is_landlord = True
            
            logger.info(f"玩家{self.landlord_index+1}成为地主，得到底牌后的手牌: {self._format_cards(self.players[self.landlord_index].hand_cards)}")
            
            # 地主先出牌
            self.current_player_index = self.landlord_index
            return True
        else:
            # 如果没人叫地主，重新发牌
            logger.info("没有玩家叫地主，重新发牌")
            return False
    
    def play_game(self):
        """进行游戏主循环"""
        # 发牌
        self.deal_cards()
        
        # 叫地主，如果没人叫地主则重新发牌
        while not self.bid_for_landlord():
            self.deal_cards()
        
        # 游戏主循环
        while not self.game_over:
            # 当前玩家
            player = self.players[self.current_player_index]
            
            # 判断是否需要跟牌
            is_follow = len(self.last_played_cards) > 0 and self.last_player_index != self.current_player_index
            
            # 获取上家出牌信息
            last_player_is_landlord = (self.last_player_index == self.landlord_index)
            
            # 使用LLM决策出牌
            played_cards = player.decide_play_cards(
                player.hand_cards,
                self.last_played_cards,
                self.last_player_index,
                last_player_is_landlord,
                self.current_player_index,
                self.current_player_index == self.landlord_index,
                is_follow
            )
            
            # 打印出牌信息
            if played_cards:
                logger.info(f"玩家{self.current_player_index+1}出牌: {self._format_cards(played_cards)}")
                
                # 更新上家出牌信息
                self.last_played_cards = played_cards
                self.last_player_index = self.current_player_index
                
                # 从手牌中移除出的牌
                for card in played_cards:
                    player.hand_cards.remove(card)
            else:
                logger.info(f"玩家{self.current_player_index+1}不出")
            
            # 检查是否有玩家出完牌
            if len(player.hand_cards) == 0:
                self.game_over = True
                self.winner_index = self.current_player_index
                break
            
            # 轮到下一个玩家
            self.current_player_index = (self.current_player_index + 1) % 3
            
            # 如果一轮都不出，由最后出牌的玩家继续出
            if self.current_player_index == self.last_player_index:
                self.last_played_cards = []
            
            # 添加一些延迟，便于观察游戏进程
            time.sleep(0.5)
        
        # 游戏结束，显示结果
        self._show_game_result()
    
    def _show_game_result(self):
        """显示游戏结果"""
        winner_role = "地主" if self.winner_index == self.landlord_index else "农民"
        logger.info(f"游戏结束，玩家{self.winner_index+1}({winner_role})获胜！")
        
        # 显示剩余玩家的手牌
        for i, player in enumerate(self.players):
            if i != self.winner_index:
                role = "地主" if i == self.landlord_index else "农民"
                logger.info(f"玩家{i+1}({role})剩余手牌: {self._format_cards(player.hand_cards)}")
    
    def _format_cards(self, cards: List[int]) -> str:
        """将整数表示的牌转换为可读的字符串
        
        Args:
            cards: 整数表示的牌列表
            
        Returns:
            str: 可读的牌面字符串
        """
        card_map = {
            1: 'A♠', 2: '2♠', 3: '3♠', 4: '4♠', 5: '5♠', 6: '6♠', 7: '7♠', 
            8: '8♠', 9: '9♠', 10: '10♠', 11: 'J♠', 12: 'Q♠', 13: 'K♠',
            14: 'A♥', 15: '2♥', 16: '3♥', 17: '4♥', 18: '5♥', 19: '6♥', 20: '7♥',
            21: '8♥', 22: '9♥', 23: '10♥', 24: 'J♥', 25: 'Q♥', 26: 'K♥',
            27: 'A♣', 28: '2♣', 29: '3♣', 30: '4♣', 31: '5♣', 32: '6♣', 33: '7♣',
            34: '8♣', 35: '9♣', 36: '10♣', 37: 'J♣', 38: 'Q♣', 39: 'K♣',
            40: 'A♦', 41: '2♦', 42: '3♦', 43: '4♦', 44: '5♦', 45: '6♦', 46: '7♦',
            47: '8♦', 48: '9♦', 49: '10♦', 50: 'J♦', 51: 'Q♦', 52: 'K♦',
            53: '小王', 54: '大王'
        }
        return ' '.join([card_map.get(card, str(card)) for card in cards])


def run_ddz_game(api_keys: List[str] = None, 
                base_urls: List[str] = None, 
                models: List[str] = None,
                system_prompts: List[str] = None,
                use_idiot_player: List[bool] = None):
    """运行斗地主游戏
    
    Args:
        api_keys: 三个玩家的API密钥，如果为None则使用默认值
        base_urls: 三个玩家的API基础URL，如果为None则使用默认值
        models: 三个玩家使用的模型名称，如果为None则使用默认值
        system_prompts: 三个玩家的系统提示词，如果为None则使用默认提示词
        use_idiot_player: 是否使用简单AI玩家，如果为True则使用IdiotPlayer，否则使用LLMCardPlayer
    """
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 设置默认值
    if api_keys is None:
        api_keys = ["ollama"] * 3
    
    if base_urls is None:
        base_urls = ["http://localhost:11434/v1"] * 3
    
    if models is None:
        models = ["qwen2.5:32b"] * 3
    
    if system_prompts is None:
        system_prompts = [""] * 3
    
    if use_idiot_player is None:
        use_idiot_player = [False, False, False]
    
    # 创建OpenAI客户端
    clients = [
        OpenAIClient(api_key=api_keys[i], base_url=base_urls[i], model=models[i])
        for i in range(3)
    ]
    
    # 创建游戏实例
    game = DDZGame(clients, system_prompts, use_idiot_player)
    
    # 运行游戏
    game.play_game()


if __name__ == "__main__":
    run_ddz_game()
