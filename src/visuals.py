from threading import Thread

from py5canvas import *
import visual_state

_is_running    = False
_should_close  = False
_visual_thread = None
_scroll_y      = 0.0      # current scroll offset in pixels
_target_scroll = 0.0      # scroll target (follows active hop)
_user_scroll_frames = 0   # frames remaining before auto-scroll resumes

# Phosphor green palette
_GREEN_BRIGHT  = (51, 255, 51)    # active hop / all-done
_GREEN_MID     = (20, 160, 20)    # done hop
_GREEN_DIM     = (10, 55, 10)     # waiting hop
_GREEN_LABEL   = (18, 110, 18)    # field labels
_GREEN_DIVIDER = (12, 70, 12)     # row separator lines

# Layout constants
_WIN_W    = 900
_WIN_H    = 720
_ROW_PAD  = 18     # left/right padding inside each row
_LINE_H   = 15     # px per text line
_SCROLL_K = 0.12   # scroll easing factor (0–1, lower = smoother)


def _all_done(hop_state: dict) -> bool:
    return bool(hop_state) and all(
        d.get("status") == "done" for d in hop_state.values()
    )


def _text_colour(status: str, all_finished: bool) -> tuple:
    if all_finished or status == "running":
        return _GREEN_BRIGHT
    if status == "done":
        return _GREEN_MID
    return _GREEN_DIM


def setup() -> None:
    size(_WIN_W, _WIN_H)
    text_size(13)
    text_font(create_font("Consolas", 13))


def _wrap_words(value: str, max_chars: int) -> list:
    words = value.split()
    lines, current = [], ""
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ["-"]


def _draw_row(hop_id: str, hop_data: dict, y: float, all_finished: bool) -> float:
    """Draw one hop row starting at y. Returns y after the row."""
    status   = hop_data.get("status", "waiting")
    t_col    = _text_colour(status, all_finished)
    relay    = hop_data.get("relay", "-")
    row_w    = _WIN_W - _ROW_PAD * 2
    max_chars = max(8, int(row_w / 7))

    # Header line: hop_id + relay name + status
    fill(*t_col)
    text_size(14)
    text(f"{hop_id}  [{relay}]", [_ROW_PAD, y])
    fill(*_GREEN_LABEL)
    text(status.upper(), [_WIN_W - _ROW_PAD - 80, y])
    text_size(13)
    y += 26

    # Separator
    stroke(*_GREEN_DIVIDER)
    line(_ROW_PAD, y, _WIN_W - _ROW_PAD, y)
    no_stroke()
    y += 10

    # Fields
    fields = [
        ("start",    hop_data.get("start",    "-")),
        ("received", hop_data.get("received", "-")),
        ("emitted",  hop_data.get("emitted",  "-")),
        ("next",     hop_data.get("next",     "-")),
        ("stop",     hop_data.get("stop",     "-")),
    ]
    for label, value in fields:
        fill(*_GREEN_LABEL)
        text(f"{label}:", [_ROW_PAD, y])
        y += _LINE_H + 2
        fill(*t_col)
        for text_line in _wrap_words(value, max_chars):
            text(text_line, [_ROW_PAD + 12, y])
            y += _LINE_H
        y += 4

    # Bottom separator
    stroke(*_GREEN_DIVIDER)
    line(_ROW_PAD, y + 6, _WIN_W - _ROW_PAD, y + 6)
    no_stroke()
    y += 20

    return y


def _find_active_y(hop_order: list, hop_state: dict) -> float:
    """Return the y position of the currently running hop for scroll targeting."""
    y = 16.0
    for hop_id in hop_order:
        data = hop_state.get(hop_id, {})
        if data.get("status") == "running":
            return y
        # Estimate row height to advance y (approx — doesn't need to be exact)
        y += 160
    return y


def draw() -> None:
    global _is_running, _scroll_y, _target_scroll, _user_scroll_frames

    hop_order, hop_state = visual_state.snapshot()

    if _should_close:
        _is_running = False
        cleanup()
        return

    background(0)

    if not hop_order:
        fill(*_GREEN_DIM)
        text("Waiting for relay configuration...", [_ROW_PAD, 60])
        return

    finished = _all_done(hop_state)

    # Auto-scroll toward active hop only when user is not scrolling
    if _user_scroll_frames > 0:
        _user_scroll_frames -= 1
    else:
        _target_scroll = max(0.0, _find_active_y(hop_order, hop_state) - _WIN_H * 0.35)
    _scroll_y += (_target_scroll - _scroll_y) * _SCROLL_K

    # Draw all rows offset by scroll
    y = 16.0 - _scroll_y
    for hop_id in hop_order:
        hop_data = hop_state.get(hop_id, {
            "relay": "-", "status": "waiting",
            "start": "-", "received": "-",
            "emitted": "-", "next": "-", "stop": "-",
        })
        y = _draw_row(hop_id, hop_data, y, finished)

    # Scanline overlay for phosphor CRT feel
    stroke(0, 0, 0, 35)
    stroke_weight(1)
    i = 0
    while i < _WIN_H:
        line(0, i, _WIN_W, i)
        i += 3
    no_stroke()
    stroke_weight(1)


def start_visuals() -> None:
    global _is_running, _should_close, _visual_thread, _scroll_y, _target_scroll
    if _is_running:
        return
    _should_close       = False
    _scroll_y           = 0.0
    _target_scroll      = 0.0
    _user_scroll_frames = 0
    _is_running         = True
    _visual_thread = Thread(target=_run_sketch, daemon=False)
    _visual_thread.start()


def stop_visuals() -> None:
    # Keep the visual window open after relay completion.
    return


def _run_sketch() -> None:
    global _is_running
    try:
        run()
    finally:
        _is_running = False


def mouse_wheel(event) -> None:
    global _target_scroll, _user_scroll_frames
    delta = getattr(event, "y", 0) or getattr(event, "delta", 0)
    _target_scroll = max(0.0, _target_scroll + delta * 30)
    _user_scroll_frames = 90  # ~3 s at 30 fps before auto-scroll resumes


def key_pressed() -> None:
    global _should_close
    if key in ("q", "Q", "\x1b"):
        _should_close = True
