from datetime import datetime
from threading import Lock

_lock = Lock()
_hop_order = []   # list of hop_ids in sequence order
_hop_state = {}   # hop_id -> state dict


def _now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _fit_text(text: str, limit: int = 200) -> str:
    if not text:
        return "-"
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def _blank_hop_state(relay_name: str = "-") -> dict:
    return {
        "relay": relay_name,
        "status": "waiting",
        "start": "-",
        "received": "-",
        "emitted": "-",
        "next": "-",
        "stop": "-",
    }


def configure_hops(hop_sequence: list) -> None:
    """Called before the run starts. hop_sequence is a list of relay names in hop order."""
    with _lock:
        global _hop_order, _hop_state
        _hop_order = [f"hop_{i + 1:02d}" for i in range(len(hop_sequence))]
        _hop_state = {
            f"hop_{i + 1:02d}": _blank_hop_state(relay_name)
            for i, relay_name in enumerate(hop_sequence)
        }


def hop_start(hop_id: str, relay_name: str, received: str) -> None:
    with _lock:
        if hop_id not in _hop_state:
            _hop_order.append(hop_id)
            _hop_state[hop_id] = _blank_hop_state(relay_name)
        _hop_state[hop_id].update({
            "relay":    relay_name,
            "status":   "running",
            "start":    _now_str(),
            "received": _fit_text(received),
            "emitted":  "-",
            "next":     "-",
            "stop":     "-",
        })


def hop_stop(hop_id: str, relay_name: str, emitted: str, next_relay: str) -> None:
    with _lock:
        if hop_id not in _hop_state:
            _hop_order.append(hop_id)
            _hop_state[hop_id] = _blank_hop_state(relay_name)
        _hop_state[hop_id].update({
            "status":  "done",
            "emitted": _fit_text(emitted),
            "next":    next_relay,
            "stop":    _now_str(),
        })


def snapshot() -> tuple[list[str], dict]:
    with _lock:
        return list(_hop_order), {k: dict(v) for k, v in _hop_state.items()}
