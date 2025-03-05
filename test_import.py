#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试导入server模块
"""

import os
import sys

# 添加当前目录到Python路径
current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, current_dir)

print(f"当前目录: {current_dir}")
print(f"Python路径: {sys.path}")

try:
    import server
    print("成功导入server模块")
    print(f"server模块路径: {server.__file__}")
    
    try:
        from server.app import main
        print("成功导入server.app.main函数")
    except ImportError as e:
        print(f"导入server.app.main失败: {e}")
        
except ImportError as e:
    print(f"导入server模块失败: {e}") 