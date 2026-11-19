"""Delivery log: no false 'confirmed' while Camfrog is unreachable; bounded in memory."""

import threading
import time

from autodj.adapters import Composite, NullAdapter
from autodj.config import Config
from autodj.engine import FAIL_DROPPED, MAX_DELIVERY_RECORDS, Engine


def _run_sender(e: Engine, text: str) -> dict:
    e.outbox.put(text)
    th = threading.Thread(target=e._sender, daemon=True)
    th.start()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        recs = [r for r in e._delivery_attempts.values() if r["text"] == text]
        if recs and recs[0]["stage"] != "attempted":
            break
        time.sleep(0.02)
    e.stop_evt.set()
    th.join(2)
    return [r for r in e._delivery_attempts.values() if r["text"] == text][0]


def test_null_adapter_message_is_dropped_not_confirmed():
    e = Engine(Config(), Composite(NullAdapter(), NullAdapter()))
    rec = _run_sender(e, "hello room")
    assert rec["stage"] == "failed" and rec["category"] == FAIL_DROPPED
    assert e._send_failure_count == 0  # dropped is not a send failure (no suspension)


def test_real_adapter_message_is_confirmed():
    class Ok(NullAdapter):
        delivers = True

        def send(self, text):
            pass

    e = Engine(Config(), Composite(Ok(), Ok()))
    assert _run_sender(e, "hello room")["stage"] == "confirmed"


def test_delivery_records_are_bounded():
    e = Engine(Config(), NullAdapter())
    for i in range(MAX_DELIVERY_RECORDS + 50):
        e.log_delivery(f"m{i}", "attempted")
    assert len(e._delivery_attempts) == MAX_DELIVERY_RECORDS
    assert [r["text"] for r in e._delivery_attempts.values()][-1] == f"m{MAX_DELIVERY_RECORDS + 49}"
