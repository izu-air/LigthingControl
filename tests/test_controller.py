from unified_lighting.controller import select_due_devices


class FakeDevice:
    def __init__(self, name: str, min_update_interval: float = 0.0):
        self.name = name
        self.min_update_interval = min_update_interval


def test_first_tick_sends_to_everyone():
    fast = FakeDevice("fast")
    slow = FakeDevice("slow", min_update_interval=1.5)
    due = select_due_devices([fast, slow], (10, 10, 10), {}, {}, now=0.0, min_change_threshold=4)
    assert due == [fast, slow]


def test_slow_device_is_skipped_until_its_interval_elapses():
    slow = FakeDevice("slow", min_update_interval=1.5)
    last_sent_time = {slow: 10.0}
    last_sent_color = {slow: (0, 0, 0)}

    due = select_due_devices([slow], (200, 0, 0), last_sent_color, last_sent_time, now=11.0, min_change_threshold=4)
    assert due == []

    due = select_due_devices([slow], (200, 0, 0), last_sent_color, last_sent_time, now=11.6, min_change_threshold=4)
    assert due == [slow]


def test_small_color_change_below_threshold_is_skipped():
    fast = FakeDevice("fast")
    last_sent_time = {fast: 0.0}
    last_sent_color = {fast: (100, 100, 100)}

    due = select_due_devices([fast], (101, 100, 100), last_sent_color, last_sent_time, now=1.0, min_change_threshold=4)
    assert due == []

    due = select_due_devices([fast], (105, 100, 100), last_sent_color, last_sent_time, now=1.0, min_change_threshold=4)
    assert due == [fast]


def test_devices_are_independent():
    fast = FakeDevice("fast")
    slow = FakeDevice("slow", min_update_interval=1.5)
    last_sent_time = {fast: 0.9, slow: 0.9}
    last_sent_color = {fast: (0, 0, 0), slow: (0, 0, 0)}

    due = select_due_devices(
        [fast, slow], (50, 50, 50), last_sent_color, last_sent_time, now=1.0, min_change_threshold=4
    )
    assert due == [fast]
