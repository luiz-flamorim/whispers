from threading import Thread

import glfw
from py5canvas import *
import visual_state

_is_running      = False
_should_close    = False
_visual_thread   = None
_scroll_y        = 0.0    # current scroll offset in pixels
_target_scroll   = 0.0    # scroll target (used during auto-follow)
_follow_mode     = True   # True = auto-follow active hop; False = user is in control
_hop_count_input = "5"    # editable hop count string (updated in setup)
_chain_started   = False  # True once user presses SPACE

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

# Fixed layout: header → info panel → log → scrollable cards
_HEADER_H  = 56                       # title bar
_INFO_H    = 140                      # description + instructions + controls
_LOG_LINES = 4                        # visible log lines
_LOG_H     = _LOG_LINES * 18 + 20    # log panel height  (4×18 + 20 = 92)
_LOG_START = _HEADER_H + _INFO_H     # y where log panel begins
_FIXED_H   = _LOG_START + _LOG_H     # total fixed area above scrollable cards

_DESC = (
    "A telephone game powered by local AI. Speak a sentence and watch it transform",
    "hop by hop as it passes through a chain of language models.",
)
_STEPS = (
    "  1.  Set the number of hops using the number keys (backspace to correct)",
    "  2.  Press SPACE to enable the microphone and start recording",
    "  3.  Speak your sentence when the recording is on",
)


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
    global _hop_count_input
    size(_WIN_W, _WIN_H)
    text_size(13)
    text_font(create_font("Consolas", 13))
    _hop_count_input = str(visual_state.get_chain_length())


def _draw_header(finished: bool, hop_count: int) -> None:
    fill(0)
    no_stroke()
    rect(0, 0, _WIN_W, _HEADER_H)

    fill(*_GREEN_BRIGHT)
    text_size(22)
    text("WHISPER CHAIN", [_ROW_PAD, 40])

    if hop_count > 0:
        status = "COMPLETE" if finished else "RUNNING…"
        label  = f"{hop_count} HOPS  ·  {status}"
    else:
        label = "STANDBY"
    fill(*(_GREEN_BRIGHT if finished else _GREEN_LABEL))
    text_size(11)
    text(label, [_WIN_W - _ROW_PAD - 170, 40])

    stroke(*_GREEN_DIVIDER)
    stroke_weight(1)
    line(0, _HEADER_H - 1, _WIN_W, _HEADER_H - 1)
    no_stroke()
    text_size(13)


_CW = 6.6   # estimated char width for 11pt Consolas (used for segment drawing)


def _draw_info(follow_mode: bool, hop_input: str, chain_started: bool) -> None:
    fill(0)
    no_stroke()
    rect(0, _HEADER_H, _WIN_W, _INFO_H)

    text_size(11)

    # --- Description ---
    y = _HEADER_H + 18
    for desc_line in _DESC:
        fill(*_GREEN_LABEL)
        text(desc_line, [_ROW_PAD, y])
        y += 16

    # Thin separator
    stroke(*_GREEN_DIVIDER)
    stroke_weight(1)
    line(_ROW_PAD, _HEADER_H + 43, _WIN_W - _ROW_PAD, _HEADER_H + 43)
    no_stroke()

    # Right column: both HOPS and RECORDING start at the same x
    # "RECORDING: [ on]" is the widest (16 chars); leave a small right margin
    right_x = int(_WIN_W - _ROW_PAD - 16 * _CW - 6)

    hop_str   = hop_input.rjust(3) if hop_input else "  1"
    recording = visual_state.is_recording()
    rec_str   = " on" if recording else "off"

    # --- Numbered steps ---
    y = _HEADER_H + 59
    for i, step in enumerate(_STEPS):
        fill(*_GREEN_MID)
        text(step, [_ROW_PAD, y])
        fill(*_GREEN_BRIGHT)
        if i == 0:
            text(f"HOPS: [{hop_str}]", [right_x, y])
        elif i == 1:
            text(f"RECORDING: [{rec_str}]", [right_x, y])
        y += 16

    # --- Controls (one blank line gap after steps) ---
    cy = y + 16
    box  = "\u25a0" if follow_mode else "\u25a1"   # ■ / □
    segs = [
        ("Controls  ",  False),
        ("\u2191/\u2193", True),  (": Scroll   ", False),
        ("PgUp/Dn",      True),  (": Jump   ",   False),
        ("Q/Esc",        True),  (": Quit    ",  False),
        ("F",            True),  (": Follow [",  False),
        (box,            True),  ("]",           False),
    ]
    x = float(_ROW_PAD)
    for seg_txt, bright in segs:
        fill(*(_GREEN_BRIGHT if bright else _GREEN_MID))
        text(seg_txt, [x, cy])
        x += len(seg_txt) * _CW

    # Bottom border
    stroke(*_GREEN_DIVIDER)
    stroke_weight(1)
    line(0, _HEADER_H + _INFO_H - 1, _WIN_W, _HEADER_H + _INFO_H - 1)
    no_stroke()
    text_size(13)


def _draw_log(log_lines: list) -> None:
    fill(0)
    no_stroke()
    rect(0, _LOG_START, _WIN_W, _LOG_H)

    fill(*_GREEN_LABEL)
    text_size(10)
    text("LOG", [_WIN_W - _ROW_PAD - 22, _LOG_START + 20])

    visible = log_lines[-_LOG_LINES:] if log_lines else []
    y = _LOG_START + 22
    text_size(12)
    for msg in visible:
        fill(*_GREEN_MID)
        text(msg, [_ROW_PAD, y])
        y += 18

    stroke(*_GREEN_DIVIDER)
    stroke_weight(1)
    line(0, _LOG_START + _LOG_H - 1, _WIN_W, _LOG_START + _LOG_H - 1)
    no_stroke()
    text_size(13)


def _draw_scrollbar(scroll_y: float, total_h: float) -> None:
    viewport_h = _WIN_H - _FIXED_H
    if total_h <= viewport_h:
        return

    track_x = float(_WIN_W - 6)
    track_y = float(_FIXED_H)
    track_h = float(viewport_h)

    # Track
    stroke(*_GREEN_DIVIDER)
    stroke_weight(2)
    line(track_x, track_y, track_x, track_y + track_h)

    # Thumb
    thumb_h = max(20.0, track_h * (viewport_h / total_h))
    scroll_range = max(1.0, total_h - viewport_h)
    thumb_y = track_y + (scroll_y / scroll_range) * (track_h - thumb_h)
    thumb_y = max(track_y, min(thumb_y, track_y + track_h - thumb_h))

    stroke(*_GREEN_MID)
    stroke_weight(4)
    line(track_x, thumb_y, track_x, thumb_y + thumb_h)

    no_stroke()
    stroke_weight(1)


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
    y += 20

    # Separator
    stroke(*_GREEN_DIVIDER)
    line(_ROW_PAD, y, _WIN_W - _ROW_PAD, y)
    no_stroke()
    y += 14

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
    """Return the scroll-space y of the currently running hop (0 = top of relay area)."""
    y = 0.0
    for hop_id in hop_order:
        data = hop_state.get(hop_id, {})
        if data.get("status") == "running":
            return y
        y += 160
    return y


def draw() -> None:
    global _is_running, _scroll_y, _target_scroll, _follow_mode, _hop_count_input, _chain_started

    hop_order, hop_state = visual_state.snapshot()
    log_lines            = visual_state.get_log()

    if _should_close:
        _is_running = False
        glfw.set_window_should_close(sketch.window, True)
        return

    background(0)
    finished = _all_done(hop_state)

    # --- Scrollable relay cards ---
    total_content_h = 0.0
    if hop_order:
        if _follow_mode:
            scroll_area_h  = _WIN_H - _FIXED_H
            _target_scroll = max(0.0, _find_active_y(hop_order, hop_state) - scroll_area_h * 0.3)
            _scroll_y += (_target_scroll - _scroll_y) * _SCROLL_K

        content_start = _FIXED_H + 16
        y = content_start - _scroll_y
        for hop_id in hop_order:
            hop_data = hop_state.get(hop_id, {
                "relay": "-", "status": "waiting",
                "start": "-", "received": "-",
                "emitted": "-", "next": "-", "stop": "-",
            })
            y = _draw_row(hop_id, hop_data, y, finished)
        total_content_h = (y + _scroll_y) - content_start

    # --- Fixed panels drawn on top ---
    _draw_header(finished, len(hop_order))
    _draw_info(_follow_mode, _hop_count_input, _chain_started)
    _draw_log(log_lines)
    _draw_scrollbar(_scroll_y, total_content_h)

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
    global _is_running, _should_close, _visual_thread, _scroll_y, _target_scroll, _follow_mode, _chain_started
    if _is_running:
        return
    _should_close  = False
    _scroll_y      = 0.0
    _target_scroll = 0.0
    _follow_mode   = True
    _chain_started = False
    _is_running    = True
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


_SCROLL_STEP = 60  # pixels per keypress


def key_pressed(k=None) -> None:
    # Accept k from py5canvas (current key, always fresh).
    # The global `key` is one frame stale due to when update_globals() runs.
    global _should_close, _target_scroll, _scroll_y, _follow_mode
    global _hop_count_input, _chain_started
    k = k if k is not None else key
    if k in ("q", "Q", "\x1b"):
        _should_close = True
        if not _chain_started:
            visual_state.request_quit()
    elif k in ("f", "F"):
        _follow_mode = not _follow_mode
    elif k == " " and not _chain_started:
        _chain_started = True
        n = max(1, min(999, int(_hop_count_input))) if _hop_count_input else 5
        visual_state.request_start(n)
    elif k.isdigit() and not _chain_started:
        raw = _hop_count_input + k
        # strip leading zeros; keep at most 3 digits
        _hop_count_input = str(int(raw))[:3] if raw else k
    elif k == "BACKSPACE" and not _chain_started:
        _hop_count_input = _hop_count_input[:-1]
    elif k == "DOWN":
        _follow_mode = False
        _scroll_y += _SCROLL_STEP
        _target_scroll = _scroll_y
    elif k == "UP":
        _follow_mode = False
        _scroll_y = max(0.0, _scroll_y - _SCROLL_STEP)
        _target_scroll = _scroll_y
    elif k == "PAGE_DOWN":
        _follow_mode = False
        _scroll_y += _WIN_H * 0.8
        _target_scroll = _scroll_y
    elif k == "PAGE_UP":
        _follow_mode = False
        _scroll_y = max(0.0, _scroll_y - _WIN_H * 0.8)
        _target_scroll = _scroll_y
