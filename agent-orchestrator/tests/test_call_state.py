import pytest
from call_state import CallState, CallStateManager


def test_call_state_defaults():
    state = CallState(fs_uuid="test-uuid")
    assert state.biz_type == ""
    assert state.turn_count == 0
    assert state.silence_count == 0
    assert state.identity_verified is False


def test_manager_set_get():
    mgr = CallStateManager()
    state = CallState(fs_uuid="uuid-1", biz_type="marketing")
    mgr.set("uuid-1", state)
    assert mgr.get("uuid-1").biz_type == "marketing"


def test_manager_remove():
    mgr = CallStateManager()
    mgr.set("uuid-1", CallState(fs_uuid="uuid-1"))
    mgr.remove("uuid-1")
    assert mgr.get("uuid-1") is None


def test_manager_list():
    mgr = CallStateManager()
    mgr.set("a", CallState(fs_uuid="a"))
    mgr.set("b", CallState(fs_uuid="b"))
    assert len(mgr.list_active()) == 2
