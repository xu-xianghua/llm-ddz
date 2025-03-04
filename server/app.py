import asyncio
import logging.config
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.websocket
from tornado.process import cpu_count

from api.auth import IndexHandler, LoginHandler, UserInfoHandler
from api.game.views import SocketHandler
from config import DEBUG, LOGGING, PORT, SECRET_KEY, TEMPLATE_ROOT, STATIC_ROOT, STATIC_URL

logging.config.dictConfig(LOGGING)


class Application(tornado.web.Application):
    def __init__(self):
        settings = {
            'debug': DEBUG,
            'cookie_secret': SECRET_KEY,
            'xsrf_cookies': False,
            'gzip': False,
            'autoescape': 'xhtml_escape',
            'template_path': TEMPLATE_ROOT,
            'static_path': STATIC_ROOT,
            'static_url_prefix': STATIC_URL,
            'login_url': '/login',
        }

        url_patterns = [
            ('/', IndexHandler),
            ('/login', LoginHandler),
            ('/userinfo', UserInfoHandler),
            ('/ws', SocketHandler),
        ]
        super().__init__(url_patterns, **settings)
        self.executor = ThreadPoolExecutor(cpu_count() * 2)
        self.allow_robot = True


async def main():
    try:
        app = Application()
        app.listen(PORT)
        logging.info(f'server on http://127.0.0.1:{PORT}')
        await asyncio.Event().wait()
    except OSError as e:
        if e.errno == 48:  # Address already in use
            logging.error(f"端口 {PORT} 已被占用，请先关闭占用该端口的进程")
        else:
            logging.error(f"启动服务器时发生错误: {e}")
    except Exception as e:
        logging.error(f"启动服务器时发生未知错误: {e}")


if __name__ == '__main__':
    asyncio.run(main())
