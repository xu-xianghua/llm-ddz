import asyncio
import base64
import json
import logging
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Optional, Awaitable, Dict, Union, Any

from tornado.web import RequestHandler, HTTPError

from config import SECRET_KEY


class JwtMixin(object):

    @staticmethod
    def jwt_encode(payload: Dict[str, Union[str, int]]) -> str:
        # 简化JWT编码，设置1小时过期时间
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        data = {'exp': expires.timestamp(), **payload}
        json_str = json.dumps(data)
        return base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    @staticmethod
    def jwt_decode(token) -> Optional[Dict[str, Union[str, int]]]:
        if not token:
            return None
        try:
            # 解码JWT
            json_str = base64.b64decode(token).decode('utf-8')
            data = json.loads(json_str)
            
            # 检查是否过期
            if 'exp' in data and datetime.fromtimestamp(data['exp'], tz=timezone.utc) < datetime.now(timezone.utc):
                logging.error('Token expired')
                return None
                
            return data
        except Exception as e:
            logging.error('Token decode error: %s', e)
            return None

    @staticmethod
    def parse_token(headers):
        header = headers.get('Authorization')
        if header:
            parts = header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                return parts[1]
        return None


class RestfulHandler(RequestHandler):
    required_fields = ()

    def prepare(self):
        self.request.remote_ip = self.client_ip

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.set_header('Access-Control-Allow-Headers', 'X-PINGOTHER, Content-Type')
        self.set_header('Access-Control-Allow-Credentials', 'true')

    def get_json_data(self) -> Dict[str, Any]:
        json_data: Dict[str, Any] = json.loads(self.request.body)
        if self.required_fields:
            for field in self.required_fields:
                if field not in json_data:
                    raise HTTPError(HTTPStatus.BAD_REQUEST, reason=f'The field "{field}" is required')
        return json_data

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        cookie = self.get_secure_cookie('userinfo')
        if cookie:
            return json.loads(cookie)
        return None

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        self.finish(json.dumps({"detail": self._reason}))

    @property
    def client_ip(self) -> str:
        headers = self.request.headers
        return headers.get('X-Forwarded-For', headers.get('X-Real-Ip', self.request.remote_ip))

    async def run_in_executor(self, func, *args):
        executor = self.application.executor
        return await asyncio.get_running_loop().run_in_executor(executor, func, *args)
