import logging
import os
from typing import Dict, Optional, Union, Type

from .player import Player
from .room import Room
from .llmroom import LLMRoom, create_llm_room

# 尝试导入LLM玩家
try:
    from agent.llmplayer import LLMPlayer, create_llm_player
    HAS_LLM_PLAYER = True
except ImportError:
    HAS_LLM_PLAYER = False
    logging.warning("未能导入LLM玩家，将使用普通玩家")


class GlobalVar(object):
    total_room_count = 0
    __players__: Dict[int, Player] = {}
    # 简化为只有一个房间
    __single_room: Optional[Room] = None
    
    # LLM玩家配置
    USE_LLM_PLAYER = os.environ.get('USE_LLM_PLAYER', 'false').lower() == 'true'
    LLM_API_KEY = os.environ.get('LLM_API_KEY', 'ollama')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'http://localhost:11434/v1')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'qwen2.5:32b')
    LLM_DECISION_DELAY = float(os.environ.get('LLM_DECISION_DELAY', '1.0'))

    @classmethod
    def room_list(cls):
        # 简化逻辑，只返回单个房间
        if cls.__single_room:
            return [{'level': cls.__single_room.level, 'number': cls.__single_room.size()}]
        return [{'level': 1, 'number': 0}]

    @classmethod
    def find_player(cls, uid: int, *args, **kwargs) -> Player:
        if uid not in cls.__players__:
            # 创建普通玩家
            logging.info(f"创建普通玩家: {uid}")
            cls.__players__[uid] = Player(uid, *args, **kwargs)
                
        return cls.__players__[uid]

    @classmethod
    def find_player_room_id(cls, uid: int) -> int:
        player = cls.__players__.get(uid)
        if player and player.room:
            return player.room.room_id
        return -1

    @classmethod
    def remove_player(cls, uid: int):
        cls.__players__.pop(uid, None)

    @classmethod
    def new_room(cls, level: int, allow_robot: bool) -> Room:
        # 如果已经有房间，无论状态如何，都直接返回现有房间
        if cls.__single_room:
            logging.info(f'已存在房间，返回现有房间: {cls.__single_room.room_id}, 状态: {"满" if cls.__single_room.is_full() else "未满"}, 人数: {cls.__single_room.size()}')
            return cls.__single_room
            
        # 只有在没有房间时才创建新房间
        logging.info(f'不存在房间，创建新房间，级别: {level}, 允许机器人: {allow_robot}')
        if cls.USE_LLM_PLAYER and allow_robot:
            # 使用LLM玩家创建房间
            llm_config = {
                'api_key': cls.LLM_API_KEY,
                'base_url': cls.LLM_BASE_URL,
                'model': cls.LLM_MODEL,
                'decision_delay': cls.LLM_DECISION_DELAY
            }
            room = create_llm_room(cls.gen_room_id(), level, allow_robot, llm_config)
            logging.info(f'创建LLM房间: {room.room_id}')
        else:
            # 使用普通机器人创建房间
            room = Room(cls.gen_room_id(), level, allow_robot)
            logging.info(f'创建普通房间: {room.room_id}')
            
        cls.__single_room = room
        logging.info('ROOM[%s] CREATED', room)
        return room

    @classmethod
    def find_room(cls, room_id: int, level: int, allow_robot: bool) -> Room:
        # 如果已经有房间，无论ID是什么，都返回现有房间
        if cls.__single_room:
            # 记录房间ID匹配情况
            if cls.__single_room.room_id != room_id:
                logging.warning(f'请求的房间ID {room_id} 与现有房间ID {cls.__single_room.room_id} 不匹配，但仍然返回现有房间')
            
            # 如果房间已满，记录日志但仍然返回现有房间
            if cls.__single_room.is_full():
                logging.warning(f'房间 {cls.__single_room.room_id} 已满，但仍然返回该房间')
            
            logging.info(f'找到现有房间: {cls.__single_room.room_id}, 状态: {"满" if cls.__single_room.is_full() else "未满"}, 人数: {cls.__single_room.size()}')
            return cls.__single_room
                
        # 只有在没有房间时才创建新房间
        logging.info(f'不存在房间，通过 new_room 创建新房间')
        return cls.new_room(level, allow_robot)

    @classmethod
    def on_room_changed(cls, room: Room):
        # 确保我们只处理单一房间
        if cls.__single_room and cls.__single_room.room_id == room.room_id:
            # 如果房间为空，清除引用
            if room.is_empty():
                logging.info(f'房间 {room.room_id} 为空，清除引用')
                cls.__single_room = None
                logging.info('Room[%s] CLOSED', room)
            # 如果房间已满，记录日志但不改变引用
            elif room.is_full():
                logging.info(f'房间 {room.room_id} 已满，人数: {room.size()}')
                logging.info('Room[%s] FULL', room)
            # 其他状态变化
            else:
                logging.info(f'房间 {room.room_id} 状态变化，人数: {room.size()}')
        else:
            # 如果不是单一房间，记录警告
            logging.warning(f'收到非单一房间的状态变化通知: {room.room_id}')

    @classmethod
    def gen_room_id(cls) -> int:
        cls.total_room_count += 1
        if cls.total_room_count > 999999:
            cls.total_room_count = 1
        return cls.total_room_count
