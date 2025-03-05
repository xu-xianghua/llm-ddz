# LLM斗地主AI玩家

本目录包含使用大型语言模型(LLM)实现的斗地主AI玩家。

## 功能特点

- 使用LLM进行斗地主游戏决策，包括叫地主和出牌
- 支持多种LLM模型，如OpenAI的GPT系列、Ollama本地模型等
- 可配置的决策延迟，模拟真实玩家思考时间
- 与服务器端无缝集成，可替代原有的规则引擎AI

## 文件说明

- `openaiclient.py`: OpenAI API客户端封装，支持自定义端点
- `llmagent.py`: LLM代理实现，处理与LLM的交互
- `cardplayer.py`: 斗地主卡牌玩家实现，使用LLM进行决策
- `llmplayer.py`: 服务器端玩家实现，继承自`Player`类，使用`LLMCardPlayer`进行决策

## 使用方法

### 1. 安装依赖

```bash
pip install openai
```

### 2. 配置LLM服务

如果使用OpenAI API，需要设置API密钥。如果使用Ollama本地模型，需要先安装并启动Ollama服务。

#### Ollama配置

1. 安装Ollama: https://ollama.com/
2. 拉取模型: `ollama pull qwen2.5:32b`（或其他支持的模型）
3. 启动Ollama服务: `ollama serve`

### 3. 启动使用LLM玩家的服务器

使用项目根目录下的`start_llm_server.py`脚本启动服务器:

```bash
python start_llm_server.py
```

可选参数:

- `--api-key`: LLM API密钥，默认为"ollama"
- `--base-url`: LLM API基础URL，默认为"http://localhost:11434/v1"
- `--model`: LLM模型名称，默认为"qwen2.5:32b"
- `--delay`: LLM决策延迟时间（秒），默认为1.0
- `--debug`: 启用调试模式

例如:

```bash
python start_llm_server.py --model llama3:8b --delay 0.5
```

### 4. 访问游戏

启动服务器后，在浏览器中访问: http://localhost:5000

## 开发指南

### 自定义系统提示

可以通过修改`cardplayer.py`中的`_get_default_system_prompt`方法来自定义系统提示，以改进LLM的决策能力。

### 调整决策逻辑

可以通过修改`cardplayer.py`中的`decide_call_landlord`和`decide_play_cards`方法来调整决策逻辑。

### 添加新的LLM模型

可以通过修改`openaiclient.py`来支持新的LLM模型或API。

## 故障排除

### 导入错误

如果遇到导入错误，请确保当前目录是项目根目录，并且已正确安装所有依赖。

### LLM连接错误

如果遇到LLM连接错误，请检查:

1. Ollama服务是否正在运行
2. API密钥和基础URL是否正确
3. 指定的模型是否已下载

### 决策错误

如果LLM做出不合理的决策，可以:

1. 尝试使用更强大的模型
2. 调整系统提示以提供更明确的指导
3. 增加决策延迟时间，给模型更多思考时间

## 许可证

与主项目相同的许可证。 