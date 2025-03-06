# LLM 斗地主游戏

这个项目实现了一个使用大语言模型(LLM)来玩斗地主的程序。程序不需要界面，通过字符输出展示游戏流程。

## 功能特点

- 使用LLM模型作为玩家进行决策
- 实现了完整的斗地主游戏流程：
  - 发牌
  - 抢地主
  - 出牌
  - 判断出牌是否合规
  - 判断胜负
- 支持多种LLM模型，包括本地Ollama模型和OpenAI API
- 可以混合使用LLM玩家和简单AI玩家

## 安装依赖

确保已安装所有必要的依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 运行游戏

使用默认设置运行游戏：

```bash
./run_ddz.py
```

或者：

```bash
python run_ddz.py
```

### 命令行参数

可以通过命令行参数自定义游戏设置：

```bash
python run_ddz.py --p1-model gpt-4 --p2-model qwen2.5:32b --p3-idiot
```

参数说明：

#### 玩家1参数
- `--p1-api-key`: 玩家1的API密钥，使用Ollama时可以是任意值，默认为"ollama"
- `--p1-base-url`: 玩家1的API基础URL，默认为"http://localhost:11434/v1"（Ollama的默认地址）
- `--p1-model`: 玩家1使用的模型名称，默认为"qwen2.5:32b"
- `--p1-system-prompt`: 玩家1的系统提示词，默认为空
- `--p1-idiot`: 玩家1使用简单AI策略而不是LLM，默认为False

#### 玩家2参数
- `--p2-api-key`: 玩家2的API密钥
- `--p2-base-url`: 玩家2的API基础URL
- `--p2-model`: 玩家2使用的模型名称
- `--p2-system-prompt`: 玩家2的系统提示词
- `--p2-idiot`: 玩家2使用简单AI策略而不是LLM

#### 玩家3参数
- `--p3-api-key`: 玩家3的API密钥
- `--p3-base-url`: 玩家3的API基础URL
- `--p3-model`: 玩家3使用的模型名称
- `--p3-system-prompt`: 玩家3的系统提示词
- `--p3-idiot`: 玩家3使用简单AI策略而不是LLM

#### 通用参数
- `--log-level`: 日志级别，可选值为DEBUG、INFO、WARNING、ERROR、CRITICAL，默认为INFO

### 使用Ollama本地模型

确保已安装Ollama并下载了相应的模型：

```bash
# 安装Ollama（根据操作系统不同，安装方式可能不同）
# 下载模型
ollama pull qwen2.5:32b
```

然后运行游戏：

```bash
python run_ddz.py --p1-model qwen2.5:32b --p2-model qwen2.5:32b --p3-model qwen2.5:32b
```

### 使用OpenAI API

```bash
python run_ddz.py --p1-api-key your_openai_api_key --p1-base-url https://api.openai.com/v1 --p1-model gpt-4
```

### 混合使用LLM和简单AI

```bash
python run_ddz.py --p1-model gpt-4 --p2-model qwen2.5:32b --p3-idiot
```

## 游戏规则

斗地主是一种流行的中国扑克牌游戏，基本规则如下：

1. 使用一副54张的扑克牌（包括大小王）
2. 三名玩家参与，一名玩家成为"地主"，其他两名玩家为"农民"
3. 发牌时，每名玩家获得17张牌，剩余3张作为"底牌"
4. 通过叫分决定谁成为地主，地主获得底牌
5. 地主先出牌，然后按顺时针方向轮流出牌
6. 玩家可以选择出牌或不出
7. 当一名玩家出完所有手牌时，游戏结束
8. 如果地主先出完牌，地主获胜；如果农民中有人先出完牌，农民获胜

## 代码结构

- `agent/ddzgame.py`: 斗地主游戏的核心实现
- `agent/cardplayer.py`: LLM卡牌玩家的实现
- `agent/llmplayer.py`: 基于LLM的玩家实现
- `agent/openaiclient.py`: OpenAI客户端封装
- `run_ddz.py`: 运行游戏的入口脚本

## 自定义系统提示词

可以通过命令行参数自定义每个玩家的系统提示词，以影响LLM的决策行为：

```bash
python run_ddz.py --p1-system-prompt "你是一个激进的斗地主玩家，喜欢冒险出牌。" --p2-system-prompt "你是一个保守的斗地主玩家，喜欢稳妥出牌。" --p3-system-prompt "你是一个平衡的斗地主玩家，根据局势灵活调整策略。"
```

## 注意事项

- 程序需要连接到LLM服务（如Ollama或OpenAI API）才能运行
- 使用大型模型可能会消耗较多资源，请确保您的设备有足够的计算能力
- 游戏过程中的决策质量取决于所使用的LLM模型的能力 