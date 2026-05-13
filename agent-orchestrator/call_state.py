from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CallState:
    fs_uuid: str
    biz_type: str = ""
    task_id: str = ""
    core_user_id: str = ""
    phone_hash: str = ""
    user_key: str = ""
    phone_masked: str = ""
    status: str = "created"
    turn_count: int = 0
    silence_count: int = 0
    asr_fail_count: int = 0
    llm_fail_count: int = 0
    identity_verified: bool = False
    recording_notice_played: bool = False
    recording_path: str = ""
    start_time: float = 0.0
    answer_time: float = 0.0
    last_action: Optional[dict] = None
    created_at: datetime = field(default_factory=datetime.now)


class CallStateManager:
    def __init__(self):
        self._states: dict[str, CallState] = {}

    def get(self, fs_uuid: str) -> CallState | None:
        return self._states.get(fs_uuid)

    def set(self, fs_uuid: str, state: CallState):
        self._states[fs_uuid] = state

    def remove(self, fs_uuid: str) -> CallState | None:
        return self._states.pop(fs_uuid, None)

    def list_active(self) -> list[CallState]:
        return list(self._states.values())
