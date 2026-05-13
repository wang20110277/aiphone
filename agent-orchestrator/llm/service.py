"""LLM 服务层 - 基于 LangChain ChatOpenAI，支持可插拔引擎"""
import json
import logging
from dataclasses import dataclass, field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMAction:
    """LLM 返回的动作"""
    type: str  # say | ask | handoff | end
    text: str
    intent: str = ""
    labels: dict = field(default_factory=dict)


FALLBACK_ACTION_TEXT = "抱歉，请再说一遍。"


def _parse_action_json(raw: str) -> LLMAction:
    """解析LLM返回的JSON动作"""
    try:
        data = json.loads(raw)
        return LLMAction(
            type=data.get("action", "say"),
            text=data.get("text", FALLBACK_ACTION_TEXT),
            intent=data.get("intent", ""),
            labels=data.get("labels", {}),
        )
    except (json.JSONDecodeError, KeyError):
        return LLMAction(type="say", text=FALLBACK_ACTION_TEXT)


class LLMService:
    """LLM 服务封装 - 提供对话、嵌入、健康检查"""

    def __init__(self):
        self._chat = ChatOpenAI(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout=settings.llm_timeout_sec,
            max_tokens=256,
            temperature=0.7,
        )
        self._embeddings = OpenAIEmbeddings(
            base_url=settings.llm_base_url,
            model=settings.llm_embedding_model,
        )

    async def chat(self, messages: list) -> str:
        """发送对话消息，返回文本响应"""
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        response = await self._chat.ainvoke(lc_messages)
        return response.content

    async def chat_for_action(self, messages: list) -> LLMAction:
        """发送对话并解析为动作"""
        raw = await self.chat(messages)
        return _parse_action_json(raw)

    async def get_embeddings(self, text: str) -> list[float]:
        """获取文本嵌入向量"""
        result = await self._embeddings.aembed_query(text)
        return result

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """批量获取嵌入向量"""
        return await self._embeddings.aembed_documents(texts)

    async def health_check(self) -> bool:
        """检查LLM服务可用性"""
        try:
            response = await self._chat.ainvoke([HumanMessage(content="ping")])
            return bool(response.content)
        except Exception as e:
            logger.error(f"LLM 健康检查失败: {e}")
            return False


# 模块级单例
_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _service
    if _service is None:
        _service = LLMService()
    return _service
