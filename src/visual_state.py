from datetime import datetime
from threading import Lock, Event

_lock          = Lock()
_hop_order     = []    # list of hop_ids in sequence order
_hop_state     = {}    # hop_id -> state dict
_log_lines     = []    # timestamped log messages for the canvas
_MAX_LOG       = 20    # oldest entries are dropped beyond this
_chain_length  = 5     # hop count; set by main.py via set_chain_length()
_start_event   = Event()  # set when user presses SPACE
_recording     = False  # True while transcribe_once() is active


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


def log(msg: str) -> None:
    """Append a timestamped message to the canvas log."""
    with _lock:
        _log_lines.append(f"[{_now_str()}] {msg}")
        if len(_log_lines) > _MAX_LOG:
            _log_lines.pop(0)


def get_log() -> list:
    with _lock:
        return list(_log_lines)


def set_chain_length(n: int) -> None:
    global _chain_length
    with _lock:
        _chain_length = max(1, min(999, n))


def get_chain_length() -> int:
    with _lock:
        return _chain_length


def request_start(chain_length: int) -> None:
    """Signal main.py to begin. Called from visuals when user presses SPACE."""
    global _chain_length
    with _lock:
        _chain_length = max(1, min(999, chain_length))
    _start_event.set()


def wait_for_start() -> int:
    """Block until user presses SPACE. Returns the configured chain length."""
    _start_event.wait()
    with _lock:
        return _chain_length


def is_started() -> bool:
    """True once SPACE has been pressed."""
    return _start_event.is_set()


def set_recording(active: bool) -> None:
    global _recording
    with _lock:
        _recording = active


def is_recording() -> bool:
    with _lock:
        return _recording


def snapshot() -> tuple[list[str], dict]:
    with _lock:
        return list(_hop_order), {k: dict(v) for k, v in _hop_state.items()}
