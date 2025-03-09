
from typing import List, Tuple
# from .cardrule import CardRule

# 加载规则文件
# rule_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'rule.json')
# with open(rule_path, 'r') as f:
#     card_rule = CardRule(json.load(f))
from server.api.game.rule import rule as card_rule


class IdiotPlayer:
    """改进的AI玩家，用于斗地主游戏
    
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
        # 检查手牌中的大牌数量
        big_cards = [poker for poker in (54, 53, 2, 15, 28, 41) if poker in hand_cards]
        
        # 已经有人叫过的最高分
        max_bid = max([bid for _, bid in history_calls]) if history_calls else 0
        
        # 根据大牌数量决定叫分
        if len(big_cards) >= 4:
            return min(3, max_bid + 1)  # 叫比当前最高分高1分，最高3分
        elif len(big_cards) >= 2:
            return min(2, max_bid + 1)  # 叫比当前最高分高1分，最高2分
        elif len(big_cards) >= 1:
            return min(1, max_bid + 1)  # 叫比当前最高分高1分，最高1分
        else:
            return 0  # 不叫
    
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
            return card_rule.find_best_shot(hand_cards)
        
        # 判断上家是否是队友（农民）
        ally = not last_player_is_landlord and not is_landlord
        
        # 如果是队友且剩余牌数较少，考虑不出牌
        if ally and len(last_played_cards) <= 4 and len(hand_cards) - len(last_played_cards) > 4:
            return []
        
        # 使用规则找出最佳跟牌
        best_follow = card_rule.find_best_follow(hand_cards, last_played_cards, ally)
        
        # 如果是王炸且队友牌数较多，考虑不出
        if len(best_follow) == 2 and 53 in best_follow and 54 in best_follow and ally and len(hand_cards) > 10:
            return []
        
        return best_follow
    
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
    
    def _play_any_cards(self, hand_cards: List[int]) -> List[int]:
        """自由出牌策略"""
        # 使用规则找出最佳出牌
        return card_rule.find_best_shot(hand_cards)
    
    def _follow_cards(self, hand_cards: List[int], last_played_cards: List[int]) -> List[int]:
        """跟牌策略"""
        # 使用规则找出最佳跟牌
        return card_rule.find_best_follow(hand_cards, last_played_cards, False)
    
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

