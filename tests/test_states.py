import pytest
from com.core import states


@pytest.fixture(autouse=True)
def cleanup_states():
    # Setup test user IDs
    test_user_1 = 999001
    test_user_2 = 999002
    states.clear_state(test_user_1)
    states.clear_state(test_user_2)
    yield
    states.clear_state(test_user_1)
    states.clear_state(test_user_2)


def test_set_and_get_state():
    user_id = 999001
    states.set_state(user_id, "test_step_1", {"foo": "bar", "monto": 50000})

    state = states.get_state(user_id)
    assert state is not None
    assert state["estado"] == "test_step_1"
    assert state["datos"]["foo"] == "bar"
    assert state["datos"]["monto"] == 50000
    assert states.has_state(user_id) is True


def test_clear_state():
    user_id = 999001
    states.set_state(user_id, "test_step_1", {"foo": "bar"})
    assert states.has_state(user_id) is True

    states.clear_state(user_id)
    assert states.has_state(user_id) is False
    assert states.get_state(user_id) is None


def test_persistence_across_memory_reset():
    user_id = 999002
    states.set_state(user_id, "persisted_step", {"step": 2, "value": 12345})

    # Simulate WSGI process restart by emptying RAM cache
    states._memory_fallback.clear()
    assert user_id not in states._memory_fallback

    # Should recover state from SQLite
    state = states.get_state(user_id)
    assert state is not None
    assert state["estado"] == "persisted_step"
    assert state["datos"]["step"] == 2
    assert state["datos"]["value"] == 12345


def test_set_state_default_datos():
    user_id = 999001
    states.set_state(user_id, "empty_step")
    state = states.get_state(user_id)
    assert state is not None
    assert state["estado"] == "empty_step"
    assert state["datos"] == {}
