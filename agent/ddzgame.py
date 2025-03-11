import logging
import random
import json
import os
from typing import List, Dict, Any, Optional, Tuple
import time
from collections import Counter, defaultdict
import colorama
from colorama import Fore, Style

from .cardplayer import LLMCardPlayer
from .openaiclient import OpenAIClient
from .idiotplayer import IdiotPlayer
from server.api.game.rule import rule as card_rule

# 初始化colorama
colorama.init(autoreset=True)

# 创建日志记录器
logger = logging.getLogger(__name__)

# 定义牌局信息输出函数
def print_game_info(message, color=Fore.WHITE, bold=False):
    """美观地打印牌局信息到控制台
    
    Args:
        message: 要打印的信息
        color: 文本颜色
        bold: 是否加粗
    """
    style = Style.BRIGHT if bold else ""
    print(f"{style}{color}{message}{Style.RESET_ALL}")

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
    
    def __init__(self, clients: List[OpenAIClient], system_prompts: List[str] = None, use_idiot_player: List[bool] = None, player_names: List[str] = None):
        """初始化斗地主游戏
        
        Args:
            clients: 三个OpenAI客户端，用于创建LLM玩家
            system_prompts: 三个玩家的系统提示词，如果为None则使用默认提示词
            use_idiot_player: 是否使用简单AI玩家，如果为True则使用IdiotPlayer，否则使用LLMCardPlayer
            player_names: 三个玩家的名字，如果为None则使用默认名字
        """
        if system_prompts is None:
            system_prompts = [""] * 3
        
        if use_idiot_player is None:
            use_idiot_player = [False, False, False]
        
        if player_names is None:
            player_names = [f"玩家{i+1}" for i in range(3)]
        
        # 保存玩家名字
        self.player_names = player_names
        
        # 初始化三个玩家
        self.players = []
        for i in range(3):
            if use_idiot_player[i]:
                self.players.append(IdiotPlayer(player_names[i]))
            else:
                self.players.append(LLMCardPlayer(clients[i], system_prompts[i]))
                self.players[i].name = player_names[i]  # 设置LLM玩家的名字
        
        # 初始化游戏状态
        self.bottom_cards = []
        self.landlord_index = -1
        self.current_player_index = 0
        self.last_played_cards = []
        self.last_player_index = -1
        self.game_over = False
        self.winner_index = -1
        
        print_game_info("=" * 60, Fore.CYAN, True)
        print_game_info("斗地主游戏开始", Fore.CYAN, True)
        print_game_info("=" * 60, Fore.CYAN, True)
    
    def deal_cards(self):
        """发牌并分配给玩家"""
        print_game_info("\n【发牌阶段】", Fore.YELLOW, True)
        
        # 生成一副完整的牌（54张）
        all_cards = list(range(1, 55))
        random.shuffle(all_cards)
        
        # 分配牌给三个玩家，每人17张，底牌3张
        for i in range(3):
            self.players[i].hand_cards = sorted(all_cards[i*17:(i+1)*17])
        
        self.bottom_cards = sorted(all_cards[51:])
        
        # 打印每个玩家的手牌
        for i, player in enumerate(self.players):
            logger.info(f"{self.player_names[i]}的手牌: {self._format_cards(player.hand_cards)}")
            print_game_info(f"{self.player_names[i]}的手牌: {self._format_cards(player.hand_cards)}", Fore.GREEN)
        
        logger.info(f"底牌: {self._format_cards(self.bottom_cards)}")
        print_game_info(f"底牌: {self._format_cards(self.bottom_cards)}", Fore.MAGENTA, True)
        
        # 随机选择第一个叫地主的玩家
        self.current_player_index = random.randint(0, 2)
        logger.info(f"{self.player_names[self.current_player_index]}先叫地主")
        print_game_info(f"{self.player_names[self.current_player_index]}先叫地主", Fore.BLUE)
        
        return True
    
    def bid_for_landlord(self):
        """进行叫地主流程"""
        print_game_info("\n【叫地主阶段】", Fore.YELLOW, True)
        
        history_calls = []
        max_bid = 0
        max_bidder = -1
        
        # 每个玩家依次叫分
        for _ in range(3):
            player = self.players[self.current_player_index]
            
            # 使用LLM决策叫分
            bid = player.decide_call_landlord(player.hand_cards, history_calls)
            
            logger.info(f"{self.player_names[self.current_player_index]}叫分: {bid}")
            print_game_info(f"{self.player_names[self.current_player_index]}叫分: {bid}", Fore.CYAN)
            
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
            
            logger.info(f"{self.player_names[self.landlord_index]}成为地主，得到底牌后的手牌: {self._format_cards(self.players[self.landlord_index].hand_cards)}")
            print_game_info(f"{self.player_names[self.landlord_index]}成为地主", Fore.RED, True)
            print_game_info(f"地主得到底牌后的手牌: {self._format_cards(self.players[self.landlord_index].hand_cards)}", Fore.GREEN)
            
            # 地主先出牌
            self.current_player_index = self.landlord_index
            return True
        else:
            # 如果没人叫地主，重新发牌
            logger.info("没有玩家叫地主，重新发牌")
            print_game_info("没有玩家叫地主，重新发牌", Fore.RED)
            return False
    
    def play_game(self):
        """进行游戏主循环"""
        # 发牌
        self.deal_cards()
        
        # 叫地主，如果没人叫地主则重新发牌
        while not self.bid_for_landlord():
            self.deal_cards()
        
        print_game_info("\n【出牌阶段】", Fore.YELLOW, True)
        
        # 游戏主循环
        round_count = 1
        while not self.game_over:
            # 当前玩家
            player = self.players[self.current_player_index]
            
            # 判断是否需要跟牌
            is_follow = len(self.last_played_cards) > 0 and self.last_player_index != self.current_player_index
            if not is_follow:
                print_game_info(f"第{round_count}轮", Fore.BLUE, True)
                round_count += 1
            else:
                if not self.can_follow_last_cards(player.hand_cards, self.last_played_cards):
                    logger.info(f"{self.player_names[self.current_player_index]}肯定要不起")
                    print_game_info(f"{self.current_player_index+1}-{self.player_names[self.current_player_index]}[{len(player.hand_cards)}]: 要不起", Fore.RED)
                    # 轮到下一个玩家
                    self.current_player_index = (self.current_player_index + 1) % 3
                    # 如果一轮都不出，由最后出牌的玩家继续出
                    if self.current_player_index == self.last_player_index:
                        self.last_played_cards = []            
                    time.sleep(0.1)
                    continue
            # 获取上家出牌信息
            last_player_is_landlord = (self.last_player_index == self.landlord_index)
            
            # 显示当前回合信息
            player_role = "地主" if self.current_player_index == self.landlord_index else "农民"
            # print_game_info(f"\n回合 {round_count} - {self.player_names[self.current_player_index]}({player_role})出牌", Fore.BLUE, True)
            # print_game_info(f"手牌: {self._format_cards(player.hand_cards)}", Fore.GREEN)
            
            # player 决策出牌
            played_cards = player.decide_play_cards(
                player.hand_cards,
                self.last_played_cards,
                self.last_player_index,
                last_player_is_landlord,
                self.current_player_index,
                self.current_player_index == self.landlord_index,
                is_follow
            )
            
            # 检查出牌是否合法
            if played_cards and not card_rule.is_contains(player.hand_cards, played_cards):
                logger.warning(f"{self.player_names[self.current_player_index]}出牌不合法: {self._format_cards(played_cards)}")
                played_cards = []
            
            if played_cards and is_follow:
                # 获取出牌类型
                decision_cards = card_rule._to_cards(played_cards)
                last_cards = card_rule._to_cards(self.last_played_cards)
                
                # 检查牌型是否相同
                decision_type, _ = card_rule._get_cards_value(decision_cards)
                last_type, _ = card_rule._get_cards_value(last_cards)
                
                # 比较牌的大小
                compare_result = card_rule.compare_pokers(played_cards, self.last_played_cards)
                
                if (decision_type != last_type and decision_type not in ['bomb', 'rocket']) or compare_result <= 0:
                    logger.warning(f"{self.player_names[self.current_player_index]}出牌不符合规则: {decision_type} vs {last_type}, 比较结果: {compare_result}")
                    played_cards = []

            if not is_follow:
                if not played_cards:
                    played_cards = card_rule.find_best_shot(player.hand_cards)
                else:
                    decision_cards = card_rule._to_cards(played_cards)
                    decision_type, _ = card_rule._get_cards_value(decision_cards)
                    if not decision_type:
                        logger.warning(f"{self.player_names[self.current_player_index]}出牌不是有效的牌型: {decision_type}")
                        played_cards = card_rule.find_best_shot(player.hand_cards)

            # 打印出牌信息
            if played_cards:
                logger.info(f"{self.player_names[self.current_player_index]}出牌: {self._format_cards(played_cards)}")
                print_game_info(f"{self.current_player_index+1}-{self.player_names[self.current_player_index]}[{len(player.hand_cards)}]: {self._format_cards(played_cards)}", Fore.YELLOW)
                
                # 更新上家出牌信息
                self.last_played_cards = played_cards
                self.last_player_index = self.current_player_index
                
                # 从手牌中移除出的牌
                for card in played_cards:
                    player.hand_cards.remove(card)
                
                # 显示剩余手牌
                # print_game_info(f"剩余手牌: {self._format_cards(player.hand_cards)}", Fore.GREEN)
            else:
                logger.info(f"{self.player_names[self.current_player_index]}不出")
                print_game_info(f"{self.current_player_index+1}-{self.player_names[self.current_player_index]}[{len(player.hand_cards)}]: 过", Fore.RED)
            
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
            time.sleep(0.1)
        
        # 游戏结束，显示结果
        self._show_game_result()
    
    def _show_game_result(self):
        """显示游戏结果"""
        print_game_info("\n【游戏结果】", Fore.YELLOW, True)
        
        winner_role = "地主" if self.winner_index == self.landlord_index else "农民"
        logger.info(f"游戏结束，{self.player_names[self.winner_index]}({winner_role})获胜！")
        print_game_info(f"游戏结束，{self.player_names[self.winner_index]}({winner_role})获胜！", Fore.MAGENTA, True)
        
        # 显示剩余玩家的手牌
        for i, player in enumerate(self.players):
            if i != self.winner_index:
                role = "地主" if i == self.landlord_index else "农民"
                logger.info(f"{self.player_names[i]}({role})剩余手牌: {self._format_cards(player.hand_cards)}")
                print_game_info(f"{self.player_names[i]}({role})剩余手牌: {self._format_cards(player.hand_cards)}", Fore.GREEN)
        
        print_game_info("=" * 60, Fore.CYAN, True)
    
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
    
    def can_follow_last_cards(self, hand_cards: List[int], last_cards: List[int]) -> bool:
        """判断指定玩家是否能够跟上家的牌
        
        Args:
            hand_cards: 玩家手牌
            last_cards: 上家出牌
            
        Returns:
            bool: 如果玩家能够跟上家的牌，返回True；否则返回False
        """
        # 如果没有上家出牌，或者上家就是当前玩家，则可以任意出牌
        if len(last_cards) == 0:
            return True

        # 获取上家出牌的类型和值
        last_cards_str = card_rule._to_cards(last_cards)
        last_type, last_value = card_rule._get_cards_value(last_cards_str)
        
        logger.debug(f"上家出牌: {last_cards_str}, 类型: {last_type}, 值: {last_value}")
        
        if not last_type:
            # 如果上家出牌不是有效的牌型，则可以任意出牌
            logger.debug("上家出牌不是有效的牌型，可以任意出牌")
            return True
            
        # 如果上家出的是火箭（双王），无法跟牌
        if last_type == 'rocket':
            logger.debug("上家出的是火箭（双王），无法跟牌")
            return False
            
        # 转换手牌为字符串表示
        hand_cards_str = card_rule._to_cards(hand_cards)
        logger.debug(f"手牌: {hand_cards_str}")
                
        # 检查是否有火箭
        if 'w' in hand_cards_str and 'W' in hand_cards_str:
            logger.debug("找到火箭（双王）")
            return True
        
        # 检查是否有同类型的牌能大过上家的牌
        for i, spec in enumerate(card_rule.rules[last_type]):
            if i > last_value and card_rule.is_contains(hand_cards_str, spec):
                logger.debug(f"找到同类型的牌能大过上家的牌: {spec}")
                return True
                
        # # 如果上家出的不是炸弹，任何炸弹都可以压过
        if last_type != 'bomb':            
            for spec in card_rule.rules['bomb']:
                if card_rule.is_contains(hand_cards_str, spec):
                    logger.debug(f"找到炸弹: {spec}")
                    return True
            
        logger.debug("没有找到能大过上家牌的组合")
        # 没有找到能大过上家牌的组合
        return False


def run_ddz_game(api_keys: List[str] = None, 
                base_urls: List[str] = None, 
                models: List[str] = None,
                system_prompts: List[str] = None,
                use_idiot_player: List[bool] = None,
                log_level: str = "INFO",
                player_names: List[str] = None):
    """运行斗地主游戏
    
    Args:
        api_keys: 三个玩家的API密钥，如果为None则使用默认值
        base_urls: 三个玩家的API基础URL，如果为None则使用默认值
        models: 三个玩家使用的模型名称，如果为None则使用默认值
        system_prompts: 三个玩家的系统提示词，如果为None则使用默认提示词
        use_idiot_player: 是否使用简单AI玩家，如果为True则使用IdiotPlayer，否则使用LLMCardPlayer
        log_level: 日志级别，默认为INFO
        player_names: 三个玩家的名字，如果为None则使用默认名字
    """
    # 配置日志
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'ddz_game_{time.strftime("%Y%m%d_%H%M%S")}.log')
    
    # 配置日志记录器
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # 将日志处理器添加到根记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(file_handler)
    
    # 移除控制台处理器，避免日志信息同时输出到控制台
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)
    
    logger.info(f"日志文件保存在: {log_file}")
    print_game_info(f"日志文件保存在: {log_file}", Fore.CYAN)
    
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
    
    if player_names is None:
        player_names = [f"玩家{i+1}" for i in range(3)]
    
    # 创建OpenAI客户端
    clients = [
        OpenAIClient(api_key=api_keys[i], base_url=base_urls[i], model=models[i])
        for i in range(3)
    ]
    
    # 创建游戏实例
    game = DDZGame(clients, system_prompts, use_idiot_player, player_names)
    
    # 运行游戏
    game.play_game()


if __name__ == "__main__":
    run_ddz_game()
