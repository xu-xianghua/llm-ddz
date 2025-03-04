from datetime import datetime

class User:
    """简单的用户类，不依赖数据库。"""
    
    def __init__(self, id=None, name=None, sex=1, avatar=None):
        self.id = id
        self.name = name
        self.sex = sex
        self.avatar = avatar
        
    def to_dict(self):
        return {
            'uid': self.id,
            'name': self.name,
            'sex': self.sex,
            'avatar': self.avatar
        }


class Record:
    """简单的记录类，不依赖数据库。"""
    
    def __init__(self, id=None, round=None, robot=1):
        self.id = id
        self.round = round or {}
        self.robot = robot