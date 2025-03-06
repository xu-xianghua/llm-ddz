import logging
import random
from typing import List, Dict, Any, Optional, Tuple
import time

from .cardplayer import LLMCardPlayer
from .openaiclient import OpenAIClient

logger = logging.getLogger(__name__)

# 定义牌型规则
CARD_RULES = {
    'rocket': ['wW'],
    'bomb': ['AAAA', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999', '0000', 'JJJJ', 'QQQQ', 'KKKK'],
    'single': ['A', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'J', 'Q', 'K', 'w', 'W'],
    'pair': ['AA', '22', '33', '44', '55', '66', '77', '88', '99', '00', 'JJ', 'QQ', 'KK'],
    'trio': ['AAA', '222', '333', '444', '555', '666', '777', '888', '999', '000', 'JJJ', 'QQQ', 'KKK'],
    'trio_pair': ['AAA22', '22233', '33344', '44455', '55566', '66677', '77788', '88899', '99900', '000JJ', 'JJJQQ', 'QQQKK', 'KKKAA'],
    'trio_single': ['AAA2', '2223', '3334', '4445', '5556', '6667', '7778', '8889', '9990', '000J', 'JJJQ', 'QQQK', 'KKKA'],
    'seq_single5': ['A2345', '23456', '34567', '45678', '56789', '67890', '7890J', '890JQ', '90JQK'],
    'seq_pair3': ['AABB33', '2233AA', '334455', '445566', '556677', '667788', '778899', '889900', '9900JJ', '00JJQQ', 'JJQQKK'],
    'seq_trio2': ['AABBB33', '222333', '333444', '444555', '555666', '666777', '777888', '888999', '999000', '000JJJ', 'JJJQQQ', 'QQQKKK'],
}

class IdiotPlayer:
    """简单的AI玩家，用于斗地主游戏
    
    Attributes:
        name: 玩家名称
        hand_cards: 手牌
        is_landlord: 是否是地主
    """
    
    def __init__(self, name: str):
        """初始化玩家
        
        Args:
            name: 玩家名称
        """
        self.name = name
        self.hand_cards = []
        self.is_landlord = False
    
    def decide_call_landlord(self, hand_cards: List[int], history_calls: List[Tuple[int, int]]) -> int:
        """决策是否叫地主
        
        Args:
            hand_cards: 手牌
            history_calls: 历史叫分记录，每个元素是(玩家索引, 叫分)的元组
            
        Returns:
            int: 叫分决策，0-3
        """
        # 简单策略：根据手牌中大牌的数量决定叫分
        big_cards = [card for card in hand_cards if card >= 53 or (card % 13 == 2)]
        bomb_count = self._count_bombs(hand_cards)
        
        # 已经有人叫过的最高分
        max_bid = max([bid for _, bid in history_calls]) if history_calls else 0
        
        # 根据大牌数量和炸弹数量决定叫分
        if len(big_cards) >= 4 or bomb_count >= 2:
            return min(3, max_bid + 1)  # 叫比当前最高分高1分，最高3分
        elif len(big_cards) >= 2 or bomb_count >= 1:
            return min(2, max_bid + 1)  # 叫比当前最高分高1分，最高2分
        elif len(big_cards) >= 1:
            return min(1, max_bid + 1)  # 叫比当前最高分高1分，最高1分
        else:
            return 0  # 不叫
    
    def _count_bombs(self, hand_cards: List[int]) -> int:
        """计算手牌中炸弹的数量"""
        # 统计每个点数的牌的数量
        card_counts = {}
        for card in hand_cards:
            rank = card % 13
            if rank == 0:
                rank = 13  # K
            card_counts[rank] = card_counts.get(rank, 0) + 1
        
        # 计算炸弹数量（四张相同点数的牌）
        bomb_count = sum(1 for count in card_counts.values() if count >= 4)
        
        # 检查是否有王炸（大小王）
        has_small_joker = 53 in hand_cards
        has_big_joker = 54 in hand_cards
        if has_small_joker and has_big_joker:
            bomb_count += 1
        
        return bomb_count
    
    def decide_play_cards(
        self, 
        hand_cards: List[int], 
        last_played_cards: List[int], 
        last_player_position: int,
        last_player_is_landlord: bool,
        my_position: int,
        is_landlord: bool,
        is_follow: bool = False
    ) -> List[int]:
        """决策出牌
        
        Args:
            hand_cards: 手牌
            last_played_cards: 上家出的牌
            last_player_position: 上家玩家位置
            last_player_is_landlord: 上家是否是地主
            my_position: 自己的位置
            is_landlord: 自己是否是地主
            is_follow: 是否是跟牌
            
        Returns:
            List[int]: 出牌决策，空列表表示不出
        """
        # 如果是第一个出牌的人或者上一个出牌的是自己，可以任意出牌
        if not last_played_cards or last_player_position == my_position:
            return self._play_any_cards(hand_cards)
        
        # 否则需要按规则跟牌
        return self._follow_cards(hand_cards, last_played_cards)
    
    def _play_any_cards(self, hand_cards: List[int]) -> List[int]:
        """自由出牌策略"""
        if not hand_cards:
            return []
        
        # 优先出单张
        if len(hand_cards) > 1:
            # 出最小的单张，但不是2或者王
            for card in sorted(hand_cards):
                rank = card % 13
                if rank != 2 and card < 53:  # 不是2或者王
                    return [card]
        
        # 如果只剩一张牌，直接出
        return [hand_cards[0]]
    
    def _follow_cards(self, hand_cards: List[int], last_played_cards: List[int]) -> List[int]:
        """跟牌策略"""
        # 简单策略：出比上家大的最小牌
        if not last_played_cards:
            return []
        
        # 如果上家出的是单张
        if len(last_played_cards) == 1:
            last_card = last_played_cards[0]
            for card in sorted(hand_cards):
                if self._card_value(card) > self._card_value(last_card):
                    return [card]
        
        # 其他情况暂时不出
        return []
    
    def _card_value(self, card: int) -> int:
        """计算牌的大小值"""
        if card == 54:  # 大王
            return 17
        if card == 53:  # 小王
            return 16
        
        rank = card % 13
        if rank == 0:
            rank = 13  # K
        
        # 2的大小是15
        if rank == 2:
            return 15
        
        # A的大小是14
        if rank == 1:
            return 14
        
        return rank


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
