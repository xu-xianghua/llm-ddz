#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动使用LLM玩家的斗地主服务器
"""

import os
import sys
import logging
import argparse
import subprocess

# 设置环境变量，启用LLM玩家
os.environ['USE_LLM_PLAYER'] = 'true'

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动使用LLM玩家的斗地主服务器')
    
    parser.add_argument('--api-key', dest='api_key', default='ollama',
                        help='LLM API密钥，默认为ollama')
    
    parser.add_argument('--base-url', dest='base_url', default='http://localhost:11434/v1',
                        help='LLM API基础URL，默认为http://localhost:11434/v1')
    
    parser.add_argument('--model', dest='model', default='qwen2.5:32b',
                        help='LLM模型名称，默认为qwen2.5:32b')
    
    parser.add_argument('--delay', dest='delay', type=float, default=1.0,
                        help='LLM决策延迟时间（秒），默认为1.0')
    
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help='启用调试模式')
    
    return parser.parse_args()

def setup_logging(debug=False):
    """设置日志"""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info(f"设置日志: log level: {log_level}")

def main():
    """主函数"""
    args = parse_args()
    setup_logging(args.debug)
    
    # 设置LLM玩家配置
    os.environ['LLM_API_KEY'] = args.api_key
    os.environ['LLM_BASE_URL'] = args.base_url
    os.environ['LLM_MODEL'] = args.model
    os.environ['LLM_DECISION_DELAY'] = str(args.delay)
    os.environ['USE_LLM_PLAYER'] = 'true'
    
    # 设置调试模式
    if args.debug:
        os.environ['DEBUG'] = 'true'
    
    # 启动服务器
    logging.info("启动使用LLM玩家的斗地主服务器")
    logging.info(f"LLM配置: API密钥={args.api_key}, 基础URL={args.base_url}, 模型={args.model}, 延迟={args.delay}秒")
    
    # 获取项目根目录和服务器目录
    root_dir = os.path.dirname(os.path.abspath(__file__))
    server_dir = os.path.join(root_dir, 'server')
    server_script = os.path.join(server_dir, 'app.py')
    
    if not os.path.exists(server_script):
        logging.error(f"找不到服务器脚本: {server_script}")
        sys.exit(1)
    
    # 保存当前工作目录
    original_dir = os.getcwd()
    
    try:
        # 切换到服务器目录
        os.chdir(server_dir)
        logging.info(f"切换到服务器目录: {server_dir}")
        
        # 设置PYTHONPATH环境变量，确保能够导入agent模块
        os.environ['PYTHONPATH'] = f"{root_dir}:{os.environ.get('PYTHONPATH', '')}"
        logging.info(f"设置PYTHONPATH: {os.environ['PYTHONPATH']}")
        
        # 使用subprocess运行服务器脚本
        subprocess.run([sys.executable, 'app.py'], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"运行服务器脚本时出错: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("服务器已停止")
    finally:
        # 恢复原始工作目录
        os.chdir(original_dir)

if __name__ == '__main__':
    main() 