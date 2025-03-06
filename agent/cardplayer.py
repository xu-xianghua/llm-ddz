import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import re

from .llmagent import LLMAgent, ConversationError
from .openaiclient import OpenAIClient

logger = logging.getLogger(__name__)

class LLMCardPlayerError(Exception):
    """LLM卡牌玩家异常基类"""
    pass

class CardDecisionError(LLMCardPlayerError):
    """卡牌决策错误"""
    pass

class LLMCardPlayer:
    """使用LLM进行斗地主游戏决策的卡牌玩家
    
    该类封装了与LLM交互的逻辑，用于进行斗地主游戏中的决策，
    包括是否叫地主以及出牌决策。
    
    Attributes:
        agent: LLM代理实例
        system_prompt: 系统提示文本
    """
    
    def __init__(
        self, 
        client: OpenAIClient,
        system_prompt: str = "",
        max_history: int = 10
    ):
        """初始化LLM卡牌玩家
        
        Args:
            client: OpenAI客户端实例
            system_prompt: 系统提示文本，如果为空则使用默认提示
            max_history: 保留的最大历史消息数量
        """
        if not system_prompt:
            system_prompt = self._get_default_system_prompt()
        
        self.agent = LLMAgent(client, system_prompt, max_history)
        self.system_prompt = system_prompt
        
        # 初始化牌面映射
        self._card_map = {
            1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 
            8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K',
            14: 'A', 15: '2', 16: '3', 17: '4', 18: '5', 19: '6', 20: '7',
            21: '8', 22: '9', 23: '10', 24: 'J', 25: 'Q', 26: 'K',
            27: 'A', 28: '2', 29: '3', 30: '4', 31: '5', 32: '6', 33: '7',
            34: '8', 35: '9', 36: '10', 37: 'J', 38: 'Q', 39: 'K',
            40: 'A', 41: '2', 42: '3', 43: '4', 44: '5', 45: '6', 46: '7',
            47: '8', 48: '9', 49: '10', 50: 'J', 51: 'Q', 52: 'K',
            53: 'w', 54: 'W'
        }
        
        # 反向映射，用于字符串到整数的转换
        self._str_map = {
            'A': [1, 14, 27, 40],
            '2': [2, 15, 28, 41],
            '3': [3, 16, 29, 42],
            '4': [4, 17, 30, 43],
            '5': [5, 18, 31, 44],
            '6': [6, 19, 32, 45],
            '7': [7, 20, 33, 46],
            '8': [8, 21, 34, 47],
            '9': [9, 22, 35, 48],
            '10': [10, 23, 36, 49],
            'J': [11, 24, 37, 50],
            'Q': [12, 25, 38, 51],
            'K': [13, 26, 39, 52],
            'w': [53],
            'W': [54]
        }
    
    def _card_to_str(self, card: int) -> str:
        """将整数表示的牌转换为字符串表示
        
        Args:
            card: 整数表示的牌
            
        Returns:
            str: 字符串表示的牌面
        """
        return self._card_map.get(card, str(card))
    
    def _str_to_card(self, card_str: str) -> int:
        """将字符串表示的牌转换为整数表示
        
        Args:
            card_str: 字符串表示的牌面
            
        Returns:
            int: 整数表示的牌，如果找不到对应的牌则返回-1
        """
        if card_str in self._str_map:
            # 返回第一个可用的牌值
            return self._str_map[card_str][0]
        return -1
    
    def _get_default_system_prompt(self) -> str:
        """获取默认的系统提示文本"""
        return """你是一个斗地主游戏AI玩家，精通斗地主游戏规则和策略。
你需要根据当前游戏状态做出最佳决策。

斗地主规则简介：
1. 使用一副54张牌（包括大小王）
2. 三名玩家，一名地主，两名农民
3. 地主先出牌，然后按逆时针顺序出牌
4. 玩家可以选择出牌或者不出（PASS）
5. 当一轮中其他两名玩家都选择PASS时，当前玩家获得出牌权
6. 如果地主先出完手牌，则地主胜利。若任一农民先出完手牌，则农民一方胜利。

牌型规则：
- 单张：任意一张牌
- 对子：两张相同点数的牌
- 三张：三张相同点数的牌
- 三带一：三张相同点数的牌 + 一张单牌
- 三带二：三张相同点数的牌 + 一对牌
- 顺子：五张或更多连续单牌（不包括2和王）
- 连对：三对或更多连续对子（不包括2和王）
- 飞机：两组或更多连续三张牌
- 飞机带翅膀：飞机 + 相应数量的单牌或对子
- 炸弹：四张相同点数的牌
- 王炸：大王和小王

牌面表示：
- 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A, 2 (从小到大)
- w: 小王
- W: 大王

你的回答应该简洁明了，直接给出决策结果。
"""

    def reset(self):
        self.agent.clear_history()
    
    def decide_call_landlord(self, hand_cards: List[int], history_calls: List[Tuple[int, int]]) -> int:
        """决定是否叫地主
        
        Args:
            hand_cards: 手牌列表，每张牌用整数表示
            history_calls: 历史叫分记录，每个元素为(玩家座位号, 叫分值)的元组
        
        Returns:
            int: 叫分决策，0表示不叫，1表示叫地主
            
        Raises:
            CardDecisionError: 决策过程中出现错误
        """
        logger.info("开始决策是否叫地主")
        try:
            # 将手牌转换为可读格式
            readable_cards = self._convert_cards_to_readable(hand_cards)
            logger.info(f"手牌可读格式: {readable_cards}")
            
            # 构建提示信息
            prompt = f"""当前游戏状态：
- 你的手牌：{readable_cards}
- 历史叫分：{history_calls}

请决定是否叫地主（抢地主）。
只需在<anser>标签中回答数字：
- 0：不叫
- 1：叫地主

例如：<anser>1</anser> 表示叫地主，<anser>0</anser> 表示不叫。
考虑你手牌的强度，做出最佳决策。"""
            
            # 获取LLM的决策
            # logger.info("开始调用LLM进行决策")
            response = self.agent.chat_once(prompt)
            logger.info(f"LLM响应: {response}")
            
            decision = self._parse_call_decision(response)
            logger.info(f"LLM决定{'叫地主' if decision == 1 else '不叫地主'}")
            return decision
            
        except ConversationError as e:
            logger.error(f"叫地主决策错误: {e}")
            logger.error("叫地主决策失败，抛出CardDecisionError异常")
            raise CardDecisionError(f"叫地主决策错误: {e}")
        except Exception as e:
            logger.error(f"叫地主决策过程中出现未知错误: {e}", exc_info=True)
            logger.error("叫地主决策失败，抛出CardDecisionError异常")
            raise CardDecisionError(f"叫地主决策过程中出现未知错误: {e}")
    
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
        """决定出什么牌
        
        Args:
            hand_cards: 手牌列表
            last_played_cards: 上家出的牌
            last_player_position: 上家的位置（0, 1, 2）
            last_player_is_landlord: 上家是否是地主
            my_position: 自己的位置（0, 1, 2）
            is_landlord: 是否是地主
            is_follow: 是否跟随上家出牌
        Returns:
            List[int]: 决定出的牌，空列表表示不出
            
        Raises:
            CardDecisionError: 决策过程中出现错误
        """
        try:
            # 将手牌和上家出牌转换为可读格式
            readable_hand = self._convert_cards_to_readable(hand_cards)
            readable_last = self._convert_cards_to_readable(last_played_cards) if last_played_cards else "无"
            logger.info(f"手牌: {readable_hand}, 上家出牌: {readable_last}")
            # 构建提示信息
            if is_follow:
                prompt = f"""当前游戏状态：
- 你的手牌：{readable_hand}
- 上家出牌：{readable_last}
- 上家位置：{last_player_position}
- 上家身份：{'地主' if last_player_is_landlord else '农民'}
- 你的位置：{my_position}
- 你的身份：{'地主' if is_landlord else '农民'}

出牌规则：
1. 如果上家出牌，你必须出比上家大的牌，或者选择不出（PASS）
2. 出牌必须符合牌型，例如上家出单张，你必须出单张；上家出对子，你必须出对子
3. 炸弹和火箭可以打任何牌型
4. 牌的大小顺序：3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A < 2 < 小王 < 大王
5. 同样牌型比较大小时，比较牌面点数

考虑当前游戏局势，做出符合上家出牌规则的最佳出牌决策。如果选择不出，请只回答 "<anser>PASS</anser>"。
如果要出牌，请列出要出的牌，放到<anser>标签中，例如："<anser>3 4 5 6 7</anser>"或"<anser>对3 对4</anser>"。只给出答案，不要无关的话。
"""
            else:
                prompt = f"""当前游戏状态：
- 你的手牌：{readable_hand}
- 你的位置：{my_position}
- 你的身份：{'地主' if is_landlord else '农民'}

出牌规则：
1. 首次出牌可以出任何有效的牌型
2. 牌型包括：单张、对子、三张、三带一、三带二、顺子、连对、飞机、炸弹、火箭等
3. 牌的大小顺序：3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A < 2 < 小王 < 大王

考虑当前游戏局势，做出最佳出牌决策。
你必须出牌，列出要出的牌，放到<anser>标签中，例如："<anser>3 4 5 6 7</anser>"或"<anser>对3 对4</anser>"。只给出答案，不要无关的话。
"""
            # 获取LLM的决策
            response = self.agent.chat_once(prompt)
            
            # 解析决策结果，传入手牌以便转换为真实的牌
            decision = self._parse_play_decision(response, hand_cards)
            
            # if decision:
            #     logger.info(f"LLM决定出牌: {self._convert_cards_to_readable(decision)}")
            # else:
            #     logger.info("LLM决定不出牌(PASS)")
                
            return decision
            
        except ConversationError as e:
            logger.error(f"出牌决策错误: {e}")
            raise CardDecisionError(f"出牌决策错误: {e}")
        except Exception as e:
            logger.error(f"出牌决策过程中出现未知错误: {e}")
            raise CardDecisionError(f"出牌决策过程中出现未知错误: {e}")
    
    def _parse_call_decision(self, response: str) -> int:
        """解析叫地主决策结果
        
        Args:
            response: LLM的回复文本
            
        Returns:
            int: 0表示不叫，1表示叫地主
        """
        # 从回复中提取<anser>标签内的内容
        anser_pattern = re.compile(r'<anser>(.*?)</anser>', re.IGNORECASE | re.DOTALL)
        match = anser_pattern.search(response)
        
        if match:
            anser_content = match.group(1).strip()
            logger.info(f"从回复中提取的<anser>内容: {anser_content}")
            
            # 尝试从<anser>内容中提取数字0或1
            if anser_content == '0':
                return 0
            elif anser_content == '1':
                return 1
        
        # 如果没有找到<anser>标签或内容不是0或1，尝试从整个回复中提取
        logger.warning(f"未找到有效的<anser>标签或内容不是0或1，尝试从整个回复中提取: {response}")
        
        # 尝试从回复中提取数字0或1
        num_match = re.search(r'[01]', response)
        if num_match:
            return int(num_match.group())
        
        # 如果没有找到数字，尝试从文本中判断
        if '不叫' in response or '不抢' in response or '放弃' in response:
            return 0
        elif '叫地主' in response or '抢地主' in response:
            return 1
        
        # 默认不叫
        logger.warning(f"无法解析叫地主决策，默认不叫: {response}")
        return 0
    
    def _parse_play_decision(self, response: str, hand_cards: List[int]) -> List[int]:
        """解析出牌决策结果
        
        Args:
            response: LLM的回复文本
            hand_cards: 手牌列表
            
        Returns:
            List[int]: 决定出的牌，空列表表示不出
        """
        # 从回复中提取<anser>标签内的内容
        anser_pattern = re.compile(r'<anser>(.*?)</anser>', re.IGNORECASE | re.DOTALL)
        match = anser_pattern.search(response)
        
        if not match:
            logger.warning(f"未找到<anser>标签，尝试直接从回复中提取决策")
            # 尝试直接从回复中提取决策
            anser_content = response.strip()
        else:
            anser_content = match.group(1).strip()
            
        logger.info(f"提取的决策内容: {anser_content}")
        
        # 检查是否为"不出"决策
        pass_pattern = re.compile(r'(PASS|不出|过|不要|要不起)', re.IGNORECASE)
        if pass_pattern.search(anser_content):
            logger.info("解析结果: 不出牌")
            return []
        
        # 特殊处理"王炸"
        if re.search(r'王炸|火箭|大小王|[Ww][Ww]', anser_content, re.IGNORECASE):
            # 检查手牌中是否有大小王
            has_big_joker = 54 in hand_cards
            has_small_joker = 53 in hand_cards
            
            if has_big_joker and has_small_joker:
                logger.info("解析结果: 王炸")
                return [53, 54]  # 小王和大王
            else:
                logger.warning("决策为王炸，但手牌中没有足够的王")
                return []
        
        # 特殊处理"炸弹"
        bomb_match = re.search(r'炸弹\s*([3-9TJQKA2])|炸\s*([3-9TJQKA2])|([3-9TJQKA2])\s*炸|([3-9TJQKA2])\s*炸弹', anser_content, re.IGNORECASE)
        if bomb_match:
            # 找出匹配的牌面
            face = None
            for group in bomb_match.groups():
                if group:
                    face = group
                    break
            
            if face:
                logger.info(f"解析结果: 炸弹 {face}")
                # 检查手牌中是否有4张相同的牌
                face_cards = [card for card in hand_cards if self._card_to_str(card) == face]
                if len(face_cards) >= 4:
                    return face_cards[:4]
                else:
                    logger.warning(f"决策为炸弹 {face}，但手牌中没有足够的牌")
                    return []
        
        # 将手牌按牌面值分组，以便后续转换为真实的牌
        hand_cards_by_face = {}
        for card in hand_cards:
            face = self._card_to_str(card)
            if face not in hand_cards_by_face:
                hand_cards_by_face[face] = []
            hand_cards_by_face[face].append(card)
                
        # 提取牌面表示
        # 处理常见的牌型表达方式
        card_patterns = [
            r'对([3-9TJQKA2])',   # 匹配"对X"格式
            r'一对([3-9TJQKA2])', # 匹配"一对X"格式
            r'两个([3-9TJQKA2])', # 匹配"两个X"格式
            r'三个([3-9TJQKA2])', # 匹配"三个X"格式
            r'三张([3-9TJQKA2])', # 匹配"三张X"格式
            r'四个([3-9TJQKA2])', # 匹配"四个X"格式
            r'四张([3-9TJQKA2])', # 匹配"四张X"格式
            r'([3-9TJQKA2])对',   # 匹配"X对"格式
            r'([3-9TJQKA2])\1+',  # 匹配连续重复的牌，如"JJJ"
            r'[3-9TJQKA2]',       # 匹配单个牌面
            r'10|十',             # 特别处理10
            r'[wW]'               # 匹配大小王
        ]
        
        # 提取的牌面值和对应的数量
        extracted_faces = {}
        # 已处理的位置集合，避免重复处理
        processed_positions = set()
        
        # 如果有"炸弹"或"炸"但没有指定牌面，尝试找出手牌中的炸弹
        if re.search(r'炸弹|炸', anser_content, re.IGNORECASE) and not bomb_match:
            # 查找手牌中有4张相同的牌
            for face, cards in hand_cards_by_face.items():
                if len(cards) >= 4:
                    logger.info(f"找到炸弹: {face}")
                    extracted_faces[face] = 4
                    # 标记为已处理，避免后续重复处理
                    bomb_positions = []
                    for m in re.finditer(r'炸弹|炸', anser_content, re.IGNORECASE):
                        bomb_positions.extend(range(m.start(), m.end()))
                    processed_positions.update(bomb_positions)
                    break
        
        # 特别处理10，直接从文本中提取
        ten_matches = re.finditer(r'10|十', anser_content)
        for match in ten_matches:
            if match.group() in ['10', '十']:
                # 检查位置是否已处理
                start_pos, end_pos = match.span()
                if any(pos in processed_positions for pos in range(start_pos, end_pos)):
                    continue
                
                # 标记位置为已处理
                processed_positions.update(range(start_pos, end_pos))
                
                face = '10'
                extracted_faces[face] = extracted_faces.get(face, 0) + 1
        
        # 特别处理大小王，直接从文本中提取
        joker_matches = re.finditer(r'[wW]|小王|大王', anser_content)
        for match in joker_matches:
            # 检查位置是否已处理
            start_pos, end_pos = match.span()
            if any(pos in processed_positions for pos in range(start_pos, end_pos)):
                continue
            
            # 标记位置为已处理
            processed_positions.update(range(start_pos, end_pos))
            
            joker = match.group()
            if joker in ['w', '小王']:
                face = 'w'
                extracted_faces[face] = extracted_faces.get(face, 0) + 1
            elif joker in ['W', '大王']:
                face = 'W'
                extracted_faces[face] = extracted_faces.get(face, 0) + 1
        
        # 提取其他牌面
        for pattern in card_patterns:
            if pattern in ['10|十', '[wW]']:  # 已经处理过10和大小王了
                continue
                
            matches = re.finditer(pattern, anser_content)
            for match in matches:
                # 检查位置是否已处理
                start_pos, end_pos = match.span()
                if any(pos in processed_positions for pos in range(start_pos, end_pos)):
                    continue
                
                # 标记位置为已处理
                processed_positions.update(range(start_pos, end_pos))
                
                if len(match.groups()) > 0:
                    # 处理带有分组的模式
                    face = match.group(1)
                    # 根据模式确定牌的数量
                    if '对' in pattern or '两个' in pattern:
                        count = 2
                    elif '三' in pattern:
                        count = 3
                    elif '四' in pattern:
                        count = 4
                    else:
                        # 对于连续重复的牌，计算重复次数
                        full_match = match.group(0)
                        count = len(full_match)
                else:
                    # 处理单个牌面的模式
                    face = match.group(0)
                    count = 1
                
                # 确保不是10的一部分
                if face in ['1', '0']:
                    # 检查是否是10的一部分
                    start_pos = match.start()
                    if (face == '1' and start_pos + 1 < len(anser_content) and anser_content[start_pos + 1] == '0') or \
                       (face == '0' and start_pos > 0 and anser_content[start_pos - 1] == '1'):
                        continue
                
                # 累加提取的牌面数量
                extracted_faces[face] = extracted_faces.get(face, 0) + count
        
        logger.info(f"提取的牌面及数量: {extracted_faces}")
        
        # 检查是否有足够的牌并转换为真实的牌
        result = []
        valid = True
        
        for face, count in extracted_faces.items():
            if face not in hand_cards_by_face or len(hand_cards_by_face[face]) < count:
                logger.warning(f"手牌中没有足够的 {face}，需要 {count} 张，但只有 {len(hand_cards_by_face.get(face, []))} 张")
                valid = False
                break
            
            # 使用真实的手牌
            result.extend(hand_cards_by_face[face][:count])
            # 从可用牌中移除已使用的牌
            hand_cards_by_face[face] = hand_cards_by_face[face][count:]
        
        if not valid:
            logger.warning(f"决策无效，手牌中没有足够的牌")
            return []
        
        logger.info(f"解析结果: {result}")
        return result
    
    def _convert_cards_to_readable(self, cards: List[int]) -> str:
        """将整数表示的牌转换为可读格式
        
        Args:
            cards: 整数表示的牌列表
            
        Returns:
            str: 可读格式的牌面字符串
        """
        if not cards:
            return ""
            
        readable_cards = []
        for card in sorted(cards):
            if card in self._card_map:
                readable_cards.append(self._card_map[card])
            else:
                readable_cards.append(str(card))
                
        return ' '.join(readable_cards)


# 测试代码
def test_llm_card_player():
    """测试LLM卡牌玩家功能"""
    from .openaiclient import OpenAIClient
    
    # 配置参数
    api_key = "ollama"
    base_url = "http://localhost:11434/v1"
    model = "qwen2.5:32b"
    
    try:
        # 创建客户端和卡牌玩家
        client = OpenAIClient(base_url, api_key, model)
        card_player = LLMCardPlayer(client)
        
        # 测试叫地主决策
        hand_cards = [3, 3, 4, 5, 6, 7, 8, 9, 10, 10, 11, 12, 13, 1, 2, 53, 54]
        history_calls = [(1, 0), (2, 0)]
        decision = card_player.decide_call_landlord(hand_cards, history_calls)
        print(f"叫地主决策: {decision}")
        
        # 测试出牌决策
        last_played_cards = [3, 4, 5, 6, 7]
        play_decision = card_player.decide_play_cards(
            hand_cards, 
            last_played_cards, 
            last_player_position=1,
            my_position=0,
            is_landlord=True,
            is_follow=True  # 这是跟牌场景，因为有上家出牌
        )
        print(f"出牌决策: {card_player._convert_cards_to_readable(play_decision)}")
        
    except CardDecisionError as e:
        logger.error(f"卡牌决策错误: {e}")
    except Exception as e:
        logger.error(f"测试过程中出现未知错误: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_llm_card_player()
