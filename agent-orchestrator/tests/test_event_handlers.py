import pytest
from unittest.mock import MagicMock, patch
from event_handlers import EventDispatcher
from call_state import CallStateManager


@pytest.fixture
def dispatcher():
    mgr = CallStateManager()
    conn = MagicMock()
    actions = MagicMock()
    return EventDispatcher(mgr, conn, actions)


def test_handle_channel_create(dispatcher):
    event = {"Unique-ID": "uuid-1", "Call-Direction": "outbound"}
    dispatcher.handle_channel_create(event)
    state = dispatcher.state_mgr.get("uuid-1")
    assert state is not None
    assert state.status == "created"


def test_handle_channel_hangup_cleans_state(dispatcher):
    from call_state import CallState
    dispatcher.state_mgr.set("uuid-1", CallState(fs_uuid="uuid-1", status="answered", start_time=0))
    event = {"Unique-ID": "uuid-1", "Hangup-Cause": "NORMAL_CLEARING"}
    dispatcher.handle_channel_hangup(event)
    assert dispatcher.state_mgr.get("uuid-1") is None
