"""Test that participant_count is properly tracked."""

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.adapters.base import ChatMessage
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine


def test_participant_count_tracked():
    """participant_count should track unique users in room."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    # Simulate chat messages from different users
    msg1 = ChatMessage(user="user1", text="hello", is_im=False)
    msg2 = ChatMessage(user="user2", text="hi", is_im=False)
    msg3 = ChatMessage(user="user1", text="again", is_im=False)

    eng._handle_room_message(msg1)
    eng._handle_room_message(msg2)
    eng._handle_room_message(msg3)

    # Should track 2 unique users
    assert eng.participant_count == 2
    assert eng._active_room_users == {"user1", "user2"}


def test_participant_count_initial_zero():
    """participant_count should start at 0."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    assert eng.participant_count == 0
    assert eng._active_room_users == set()
