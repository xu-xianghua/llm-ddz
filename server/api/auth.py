from typing import Optional, Awaitable

from tornado.escape import json_encode
from tornado.web import authenticated, RequestHandler

from api.base import RestfulHandler, JwtMixin
from api.game.globalvar import GlobalVar

# 简单的玩家存储
player_store = {}
next_player_id = 1


class IndexHandler(RequestHandler):

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self):
        self.render('poker.html')


class LoginHandler(RestfulHandler, JwtMixin):
    required_fields = ('name',)

    async def get(self):
        self.write({'detail': 'welcome'})

    async def post(self):
        global next_player_id
        name = self.get_json_data()['name']
        
        # 创建简单的玩家信息
        player = {
            'uid': next_player_id,
            'name': name,
            'sex': 1,  # 默认值
            'avatar': ''  # 默认空头像
        }
        
        player_store[next_player_id] = player
        next_player_id += 1

        self.set_secure_cookie('userinfo', json_encode(player))
        self.write({
            **player,
            'room': -1,  # 默认未加入房间
            'token': self.jwt_encode(player)
        })


class UserInfoHandler(RestfulHandler):

    @authenticated
    async def get(self):
        uid = self.current_user['uid']
        player = player_store.get(uid)
        
        if player:
            self.write({
                **player,
                'room': GlobalVar.find_player_room_id(player['uid']),
                'rooms': GlobalVar.room_list()
            })
        else:
            self.clear_cookie('userinfo')
            self.send_error(404, reason='Player not found')


class LogoutHandler(RestfulHandler):

    @authenticated
    def post(self):
        self.clear_cookie('userinfo')
        self.write({})
