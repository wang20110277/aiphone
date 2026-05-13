import pytest
from unittest.mock import MagicMock, patch
from memory.redis_memory import RedisHotMemory


@pytest.fixture
def memory():
    store = {}

    mock_client = MagicMock()

    def fake_hset(key, field, value):
        store.setdefault(key, {})[field] = value

    def fake_hget(key, field):
        return store.get(key, {}).get(field)

    def fake_hgetall(key):
        return store.get(key, {})

    mock_client.hset.side_effect = fake_hset
    mock_client.hget.side_effect = fake_hget
    mock_client.hgetall.side_effect = fake_hgetall
    mock_client.expire.return_value = True

    with patch("memory.redis_memory.redis.Redis.from_url", return_value=mock_client):
        yield RedisHotMemory("redis://localhost:6379/0")


def test_set_and_get(memory):
    memory.set_fact("customer_service", "user1:h1", "pref_contact_time", "周末上午")
    fact = memory.get_fact("customer_service", "user1:h1", "pref_contact_time")
    assert fact == "周末上午"


def test_get_all_facts(memory):
    memory.set_fact("marketing", "u1:h1", "do_not_call", "true")
    facts = memory.get_all_facts("marketing", "u1:h1")
    assert isinstance(facts, dict)


def test_set_do_not_call(memory):
    memory.set_do_not_call("marketing", "u1:h1")
    assert memory.get_fact("marketing", "u1:h1", "do_not_call") == "true"
