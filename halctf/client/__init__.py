"""クライアント層: 中央 Model Service への接続とモデル多段切替。"""

from halctf.client.base import ChatMessage, LLMClient, ToolCall, ToolSpec
from halctf.client.openai_compat import OpenAICompatClient

__all__ = ["ChatMessage", "LLMClient", "ToolCall", "ToolSpec", "OpenAICompatClient"]
