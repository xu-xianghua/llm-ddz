from __future__ import annotations

import logging
import random
from typing import Optional, Dict, Any

from tornado.ioloop import IOLoop

from .room import Room
from .protocol import Protocol as Pt

# 导入LLM玩家相关模块
from agent.llmplayer import create_llm_player


class LLMRoom(Room):
    """使用LLM玩家的房间类
    
    继承自Room类，重写add_robot方法，使用LLM玩家替代简单机器人。
    """
    
    def __init__(self, room_id: int, level: int = 1, allow_robot: bool = True):
        """初始化LLM房间
        
        Args:
            room_id: 房间ID
            level: 房间等级
            allow_robot: 是否允许机器人
        """
        super().__init__(room_id, level, allow_robot)
        self.llm_config = {
            'api_key': 'ollama',
            'base_url': 'http://localhost:11434/v1',
            'model': 'qwen2.5:32b',
            'system_prompt': '',
            'decision_delay': 1.0
        }
    
    def set_llm_config(self, config: Dict[str, Any]):
        """设置LLM配置
        
        Args:
            config: LLM配置字典
        """
        self.llm_config.update(config)
    
    def add_robot(self, nth=1):
        """添加LLM机器人到房间
        
        重写Room类的add_robot方法，使用LLM玩家替代简单机器人。
        
        Args:
            nth: 机器人序号
        """
        size = self.size()
        logging.info(f"尝试添加LLM机器人 #{nth}, 当前房间大小: {size}, 玩家列表: {[p.uid if p else None for p in self.players]}")
                
        if size == 0 or size == 3:
            logging.info(f"房间 {self.room_id} 不需要添加机器人: 房间为空或已满")
            return

        if nth == 1 and self.robot_no > 2:
            # limit robot number
            logging.info(f"房间 {self.room_id} 机器人数量已达上限: {self.robot_no}")
            return
        
        # 创建LLM玩家
        robot_id = (10000 + self.robot_no + 1)  
        robot_name = f'LLM-{nth}'
        
        logging.info(f"创建LLM玩家: ID={robot_id}, 名称={robot_name}")
        llm_player = create_llm_player(
            uid=robot_id,
            name=robot_name,
            api_key=self.llm_config['api_key'],
            base_url=self.llm_config['base_url'],
            model=self.llm_config['model'],
            system_prompt=self.llm_config['system_prompt'],
            decision_delay=self.llm_config['decision_delay'],
            room=self
        )
        
        # 修改：直接加入房间，而不是通过to_server消息
        from server.api.game.globalvar import GlobalVar
        
        # 设置玩家状态为WAITING
        llm_player.state = 1  # State.WAITING
        
        # 直接调用join_room方法
        if llm_player.join_room(self):
            self.sync_room()
            logging.info(f'LLM玩家 {llm_player.uid} 直接加入房间 {self.room_id}')
        else:
            logging.error(f'LLM玩家 {llm_player.uid} 无法加入房间 {self.room_id}')
        
        # 增加机器人计数
        self.robot_no += 1
        
        # 如果是第一个机器人，1秒后添加第二个
        if nth == 1:
            IOLoop.current().call_later(1, self.add_robot, nth=2)


# 创建LLM房间的工厂函数
def create_llm_room(room_id: int, level: int = 1, allow_robot: bool = True, llm_config: Optional[Dict[str, Any]] = None) -> LLMRoom:
    """创建LLM房间
    
    Args:
        room_id: 房间ID
        level: 房间等级
        allow_robot: 是否允许机器人
        llm_config: LLM配置字典
        
    Returns:
        LLMRoom: LLM房间实例
    """
    room = LLMRoom(room_id, level, allow_robot)
    
    if llm_config:
        room.set_llm_config(llm_config)
    
    return room

