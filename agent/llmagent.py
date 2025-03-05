import logging
from typing import List, Tuple, Optional, Dict, Any
from .openaiclient import OpenAIClient, OpenAIError
import re

logger = logging.getLogger(__name__)

class LLMAgentError(Exception):
    """LLM 代理异常基类"""
    pass

class ConversationError(LLMAgentError):
    """对话过程中的错误"""
    pass

class LLMAgent:
    def __init__(
        self, 
        client: OpenAIClient, 
        system_prompt: str = "",
        max_history: int = 10,
        role: str = "assistant"  
    ) -> None:
        """
        初始化 LLM 代理
        
        Args:
            client: OpenAI 客户端实例
            system_prompt: 系统提示文本
            max_history: 保留的最大历史消息数量
            role: 代理角色名称，默认为 "assistant"
        """
        self.client = client
        self.max_history = max_history
        self.conversation_history: List[Dict[str, str]] = []
        self.role = role  
        
        if system_prompt:
            self.set_system_prompt(system_prompt)
            
    def set_role(self, role: str) -> None:
        """
        设置代理角色
        
        Args:
            role: 角色名称
        """
        self.role = role
        # 更新系统提示中的角色信息
        if hasattr(self, 'system_prompt'):
            self.clear_history()  # 清空历史并重新设置系统提示
            
    def get_role(self) -> str:
        """
        获取当前角色
        
        Returns:
            str: 当前角色名称
        """
        return self.role

    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示"""
        self.system_prompt = prompt
        self.conversation_history.append({"role": "system", "content": prompt})

    def add_message(self, role: str, content: str) -> None:
        """添加消息到对话历史"""
        self.conversation_history.append({"role": role, "content": content})
        self._trim_history()

    def clear_history(self) -> None:
        """清空对话历史"""
        self.conversation_history = []
        self.set_system_prompt(self.system_prompt)

    def chat_once(self, message: str, split_think: bool = True) -> str:
        """
        进行一次对话
        
        Args:
            message: 用户消息文本
            split_think: 是否分离思考内容，默认为 True
            
        Returns:
            str: 回复文本
            
        Raises:
            ConversationError: 对话过程中出现错误
        """
        try:
            self.add_message("user", message)
            reply = self.client.generate_response(self.conversation_history)
            
            if split_think:
                # 处理思考内容
                reply, think_content = self._split_think(reply)
                if think_content:
                    logger.debug(f"Thought process ({self.role}): {think_content}")
            
            # 使用当前角色添加回复
            self.add_message(self.role, reply)
            logger.debug(f"L-L-M {self.role} 回复: {reply}")
            return reply
            
        except OpenAIError as e:
            logger.error(f"API error in conversation ({self.role}): {e}")
            raise ConversationError(f"API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in conversation ({self.role}): {e}")
            raise ConversationError(f"Unexpected error: {e}")

    def chat_multiple(self, messages: List[str], split_think: bool = True) -> List[str]:
        """
        进行多次对话
        
        Args:
            messages: 用户消息列表
            split_think: 是否分离思考内容，默认为 True
            
        Returns:
            List[str]: 每次对话的回复文本列表
        """
        return [self.chat_once(message, split_think) for message in messages]

    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取对话摘要信息"""
        return {
            "message_count": len(self.conversation_history),
            "has_system_prompt": any(
                msg["role"] == "system" 
                for msg in self.conversation_history
            ),
            "user_messages": sum(
                1 for msg in self.conversation_history 
                if msg["role"] == "user"
            ),
            "role_messages": sum(
                1 for msg in self.conversation_history 
                if msg["role"] == self.role
            ),
            "current_role": self.role
        }

    def save_conversation(self, filepath: str) -> None:
        """保存对话历史到文件"""
        import json
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            raise ConversationError(f"Failed to save conversation: {e}")

    def load_conversation(self, filepath: str) -> None:
        """从文件加载对话历史"""
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.conversation_history = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")
            raise ConversationError(f"Failed to load conversation: {e}")

    def _strip_think(self, response: str) -> str:
        """剔除回复中的 <think> ... </think> 部分"""
        return re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()

    def _split_think(self, response: str) -> Tuple[str, str]:
        """分离回复中的 <think> ... </think> 部分

        Args:
            response (str): 回复文本

        Returns:
            Tuple[str, str]: 剔除 <think> ... </think> 部分后的文本和 <think> ... </think> 部分的内容
        """
        think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
        think_content = " ".join(think_pattern.findall(response))
        stripped_response = think_pattern.sub("", response).strip()
        return stripped_response, think_content

    def _trim_history(self) -> None:
        """裁剪历史消息，保持在最大限制之内"""
        if len(self.conversation_history) > self.max_history:
            # 保留系统提示和最新的消息
            system_messages = [
                msg for msg in self.conversation_history 
                if msg["role"] == "system"
            ]
            other_messages = [
                msg for msg in self.conversation_history 
                if msg["role"] != "system"
            ]
            
            # 保留最新的消息
            kept_messages = other_messages[-self.max_history:]
            self.conversation_history = system_messages + kept_messages

def test_agent():
    """测试 LLM 代理功能"""
    api_key = "ollama"
    base_url = "http://localhost:11434/v1"
    model = "qwen2.5:32b"
    system_prompt = "你是一个有帮助的助手。"
    
    try:
        client = OpenAIClient(base_url, api_key, model)
        agent = LLMAgent(client, system_prompt)
        
        # 测试单次对话
        reply = agent.chat_once("你好，今天的天气怎么样？")
        print(f"单次对话回复: {reply}")
        
        # 测试多次对话
        messages = [
            "你能介绍一下自己吗？",
            "你可以帮我做些什么？",
            "谢谢你的回答"
        ]
        replies = agent.chat_multiple(messages)
        print("\n多次对话:")
        for i, reply in enumerate(replies, 1):
            print(f"回合 {i}: {reply}")
            
    except ConversationError as e:
        logger.error(f"对话错误: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_agent()