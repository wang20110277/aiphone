import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from memory.chat_history import get_chat_history, load_chat_history, save_turn


def test_get_chat_history():
    with patch("memory.chat_history.settings") as mock_settings:
        mock_settings.redis_url = "redis://localhost:6379/0"
        with patch("memory.chat_history.RedisChatMessageHistory") as mock_cls:
            history = get_chat_history("call123", "marketing")
            mock_cls.assert_called_once_with(
                session_id="marketing:call123",
                redis_url="redis://localhost:6379/0",
                key_prefix="cb:chat:",
                ttl=3600,
            )


@pytest.mark.asyncio
async def test_load_chat_history():
    mock_history = MagicMock()
    mock_history.aget_messages = AsyncMock(return_value=[HumanMessage(content="hello")])
    with patch("memory.chat_history.get_chat_history", return_value=mock_history):
        messages = await load_chat_history("call123", "customer_service")
    assert len(messages) == 1
    assert messages[0].content == "hello"


@pytest.mark.asyncio
async def test_save_turn():
    mock_history = MagicMock()
    mock_history.aadd_messages = AsyncMock()
    await save_turn(mock_history, "你好", "您好")
    mock_history.aadd_messages.assert_called_once()
    args = mock_history.aadd_messages.call_args[0][0]
    assert len(args) == 2
    assert isinstance(args[0], HumanMessage)
    assert isinstance(args[1], AIMessage)
    assert args[0].content == "你好"
    assert args[1].content == "您好"
