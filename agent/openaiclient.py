from typing import List, Dict, Iterator, Optional, Any
import logging
from openai import OpenAI
import time
from functools import wraps

logger = logging.getLogger(__name__)

class OpenAIError(Exception):
    """OpenAI 客户端异常基类"""
    pass

class APIError(OpenAIError):
    """API 调用错误"""
    pass

def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """错误重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # 指数退避
                    continue
            raise APIError(f"All {max_retries} attempts failed. Last error: {str(last_error)}")
        return wrapper
    return decorator

class OpenAIClient:
    """OpenAI API 客户端封装
    
    处理与 OpenAI API 的通信，支持自定义端点（如 Ollama）
    
    Attributes:
        api_key: API 密钥
        model: 模型名称
        base_url: API 基础 URL
        max_tokens: 最大生成令牌数
        temperature: 采样温度
        stream: 是否使用流式响应
        frequency_penalty: 频率惩罚系数
        presence_penalty: 存在惩罚系数
    """
    
    def __init__(
        self, 
        base_url: str,
        api_key: str, 
        model: str,
        stream: bool = False,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        frequency_penalty: float = 0,
        presence_penalty: float = 0.0
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.stream = stream
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

        # 创建 OpenAI 客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0  # 设置超时时间为60秒
        )

    @retry_on_error(max_retries=3)
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """生成对话回复
        
        Args:
            messages: 对话历史消息列表，每条消息包含 role 和 content
            
        Returns:
            模型生成的回复文本
            
        Raises:
            Exception: API 调用失败时抛出异常
        """
        logger.info(f"开始生成回复，模型: {self.model}, 消息数: {len(messages)}")
        try:
            # logger.info(f"API调用参数: model={self.model}, max_tokens={self.max_tokens}, temperature={self.temperature}")
            logger.debug(f"消息内容: {messages}")
            
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=self.stream,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty
            )
            elapsed_time = time.time() - start_time
            
            content = response.choices[0].message.content
            logger.info(f"生成回复成功，耗时: {elapsed_time:.2f}秒，回复长度: {len(content)}，回复内容: {content}")
            logger.debug(f"回复内容: {content}")
            
            return content
        except Exception as e:
            logger.error(f"生成回复失败: {e}", exc_info=True)
            raise Exception(f"Failed to generate response: {e}")

    def generate_stream_response(self, messages: List[Dict[str, str]]) -> Iterator[str]:
        """生成流式对话回复
        
        Args:
            messages: 对话历史消息列表
            
        Yields:
            生成的文本片段
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"Failed to generate stream response: {e}")

# 示例用法
if __name__ == "__main__":
    # 配置参数
    api_key = "ollama"
    base_url = "http://localhost:11434/v1"
    model = "deepseek-r1:32b"
    
    try:
        # 创建客户端
        client = OpenAIClient(base_url, api_key, model)
        
        # 测试普通对话
        messages = [{"role": "user", "content": "写一个 Python 函数来计算斐波那契数列"}]
        response = client.generate_response(messages)
        print("Regular response:", response)
        
        # 测试流式对话
        client.stream = True
        print("\nStream response:")
        for chunk in client.generate_stream_response(messages):
            print(chunk, end="", flush=True)
            
    except Exception as e:
        print(f"Error: {e}")
