"""Test case to reproduce the daemon crash bug."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_send_to_with_array_response():
    """Reproduce crash when gchat returns JSON array instead of object."""
    # Simulate what happens when gchat returns an array
    raw_response = '[{"success": true}]'  # Array, not object

    # This is what the buggy code does:
    data = json.loads(raw_response)

    # This should crash with: 'list' object has no attribute 'get'
    try:
        result = data.get("success")
        assert False, f"Expected AttributeError but got result: {result}"
    except AttributeError as e:
        assert "'list' object has no attribute 'get'" in str(e)
        print(f"✓ Reproduced crash: {e}")

def test_msg_iteration_with_non_dict():
    """Reproduce crash when messages contain non-dict items."""
    messages = [
        {"sender": {"displayName": "Alice"}, "text": "Hello"},
        ["weird", "list", "item"],  # Unexpected list in messages
    ]

    # This is what the buggy code does:
    for msg in messages:
        try:
            # Lines 122-124 in gchat.py
            if isinstance(msg.get("sender"), dict):  # CRASH on 2nd iteration
                pass
            assert isinstance(msg, dict), "Should have crashed before this point"
        except AttributeError as e:
            assert "'list' object has no attribute 'get'" in str(e)
            print(f"✓ Reproduced crash in iteration: {e}")
            break

if __name__ == "__main__":
    print("Testing daemon crash scenarios...")
    test_send_to_with_array_response()
    test_msg_iteration_with_non_dict()
    print("\n✅ All crash scenarios reproduced successfully")
