#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
from typing import List

from agent.ddzgame import run_ddz_game

def main():
    """主函数，解析命令行参数并运行斗地主游戏"""
    parser = argparse.ArgumentParser(description='使用LLM模型玩斗地主游戏')
    
    # 玩家1的参数
    parser.add_argument('--p1-api-key', type=str, default='ollama',
                        help='玩家1的API密钥，使用ollama时可以是任意值')
    parser.add_argument('--p1-base-url', type=str, default='http://localhost:11434/v1',
                        help='玩家1的API基础URL')
    parser.add_argument('--p1-model', type=str, default='qwen2.5:32b',
                        help='玩家1使用的模型名称')
    parser.add_argument('--p1-system-prompt', type=str, default='',
                        help='玩家1的系统提示词')
    parser.add_argument('--p1-idiot', action='store_true',
                        help='玩家1使用简单AI策略而不是LLM')
    
    # 玩家2的参数
    parser.add_argument('--p2-api-key', type=str, default='ollama',
                        help='玩家2的API密钥，使用ollama时可以是任意值')
    parser.add_argument('--p2-base-url', type=str, default='http://localhost:11434/v1',
                        help='玩家2的API基础URL')
    parser.add_argument('--p2-model', type=str, default='qwen2.5:32b',
                        help='玩家2使用的模型名称')
    parser.add_argument('--p2-system-prompt', type=str, default='',
                        help='玩家2的系统提示词')
    parser.add_argument('--p2-idiot', action='store_true',
                        help='玩家2使用简单AI策略而不是LLM')
    
    # 玩家3的参数
    parser.add_argument('--p3-api-key', type=str, default='ollama',
                        help='玩家3的API密钥，使用ollama时可以是任意值')
    parser.add_argument('--p3-base-url', type=str, default='http://localhost:11434/v1',
                        help='玩家3的API基础URL')
    parser.add_argument('--p3-model', type=str, default='qwen2.5:32b',
                        help='玩家3使用的模型名称')
    parser.add_argument('--p3-system-prompt', type=str, default='',
                        help='玩家3的系统提示词')
    parser.add_argument('--p3-idiot', action='store_true',
                        help='玩家3使用简单AI策略而不是LLM')
    
    # 通用参数
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='日志级别')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 收集玩家参数
    api_keys = [args.p1_api_key, args.p2_api_key, args.p3_api_key]
    base_urls = [args.p1_base_url, args.p2_base_url, args.p3_base_url]
    models = [args.p1_model, args.p2_model, args.p3_model]
    system_prompts = [args.p1_system_prompt, args.p2_system_prompt, args.p3_system_prompt]
    use_idiot_player = [args.p1_idiot, args.p2_idiot, args.p3_idiot]
    
    # 运行游戏
    run_ddz_game(
        api_keys=api_keys,
        base_urls=base_urls,
        models=models,
        system_prompts=system_prompts,
        use_idiot_player=use_idiot_player
    )

if __name__ == "__main__":
    main() 