import pytest
from unittest.mock import MagicMock
from fs_actions import FSActions, TTSProfileMap


def test_tts_profile_mapping():
    assert TTSProfileMap.get("customer_service") == "tts_customer_service_v1"
    assert TTSProfileMap.get("collection") == "tts_collection_v1"
    assert TTSProfileMap.get("marketing") == "tts_marketing_v1"


def test_asr_profile():
    assert TTSProfileMap.get_asr() == "asr_default_v1"


def test_play_legal_notice_calls_api():
    conn = MagicMock()
    conn.api.return_value = "+OK"
    actions = FSActions(conn)
    result = actions.play_legal_notice("uuid-1")
    assert result is True
    conn.api.assert_called_once()
