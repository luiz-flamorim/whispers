from threading import Thread

from py5canvas import *
import visual_state

_is_running = False
_should_close = False
_visual_thread = None



def setup() -> None:
    size(1440, 480)
    text_size(16)
    text_font(create_font("Consolas", 16))


def _draw_relay_column(relay_name: str, relay_data: dict, x: float, y: float, col_width: float) -> None:
    fill(255)
    text(relay_name, [x, y])
    y += 32

    for key in ("status", "start", "received", "emitted", "emitted_to", "stop"):
        text(f"{key}: {relay_data[key]}", [x, y])
        y += 30

    stroke(70)
    line(x + col_width, 24, x + col_width, 456)
    no_stroke()


def draw() -> None:
    global _is_running
    relay_order, relay_state = visual_state.snapshot()
    if _should_close:
        _is_running = False
        cleanup()
        return

    background(0)

    if not relay_order:
        fill(180)
        text("Waiting for relay configuration...", [32, 60])
        return

    margin_left = 24
    usable_width = 1392
    col_width = usable_width / len(relay_order)

    for idx, relay_name in enumerate(relay_order):
        x = margin_left + idx * col_width
        relay_data = relay_state.get(
            relay_name,
            {
                "status": "waiting",
                "start": "-",
                "received": "-",
                "emitted": "-",
                "emitted_to": "-",
                "stop": "-",
            },
        )
        _draw_relay_column(relay_name, relay_data, x, 56, col_width)


def start_visuals() -> None:
    global _is_running, _should_close, _visual_thread
    if _is_running:
        return
    _should_close = False
    _is_running = True
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


def key_pressed() -> None:
    global _should_close
    if key in ("q", "Q", "\x1b"):
        _should_close = True