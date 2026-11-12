"""Test that discover.py config parsing is robust."""

from camfrog_autodj.discover import update_config_text


def test_update_config_text_unquoted_value():
    """Should handle unquoted values correctly (uses single quotes)."""
    text = 'window_title_re = ".*"\n'
    updates = {"window_title_re": "new.*"}
    result = update_config_text(text, updates)
    assert "window_title_re = 'new.*'" in result


def test_update_config_text_unquoted_bare_value():
    """Should handle bare unquoted values (no quotes)."""
    text = "some_key = bare_value\n"
    updates = {"some_key": "new_value"}
    result = update_config_text(text, updates)
    assert "some_key = 'new_value'" in result


def test_update_config_text_no_duplicate_keys():
    """Should not produce duplicate keys."""
    text = 'key1 = "value1"\nkey2 = "value2"\n'
    updates = {"key1": "new_value1"}
    result = update_config_text(text, updates)
    # Count occurrences of key1
    count = result.count("key1 =")
    assert count == 1, f"Expected 1 occurrence of key1, got {count}: {result}"


def test_update_config_text_preserves_comments():
    """Should preserve trailing comments."""
    text = 'key = "value"  # comment\n'
    updates = {"key": "new_value"}
    result = update_config_text(text, updates)
    assert "# comment" in result


def test_update_config_text_adds_new_key():
    """Should add new key if not present."""
    text = 'key1 = "value1"\n'
    updates = {"key2": "value2"}
    result = update_config_text(text, updates)
    assert "key2 = 'value2'" in result


def test_update_config_text_handles_spaces():
    """Should handle various spacing."""
    text = "key = value\n"
    updates = {"key": "new"}
    result = update_config_text(text, updates)
    assert "key = 'new'" in result
