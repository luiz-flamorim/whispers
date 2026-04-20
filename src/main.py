import sys
import random
from importlib import import_module
from pathlib import Path

import chain_log

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

try:
    from visual_state import (configure_hops, hop_start, hop_stop, log as _vlog,
                               set_chain_length, wait_for_start, get_chain_length,
                               set_recording, wait_for_print_decision,
                               wait_for_next_action, reset as reset_state,
                               request_retry)
except ImportError:
    configure_hops          = None
    hop_start               = None
    hop_stop                = None
    _vlog                   = None
    set_chain_length        = None
    wait_for_start          = None
    get_chain_length        = None
    set_recording           = None
    wait_for_print_decision = None
    wait_for_next_action    = None
    reset_state             = None
    request_retry           = None


def _log(msg: str) -> None:
    """Log to the canvas panel and to stdout."""
    print(msg)
    if _vlog is not None:
        _vlog(msg)

try:
    from visuals import start_visuals, stop_visuals
except ImportError:
    start_visuals = None
    stop_visuals = None

RELAY_SYSTEM_PROMPT = "You are part of a message relay chain. Your only job is to understand what was said and, in your own words, output a short rephrase of that message for the next relay. Do not reply to the message as if in a conversation—only pass it on. If the message is a greeting (e.g. 'Hello'), a thanks, or another short phrase, still pass it as content (e.g. 'Someone said hello'). Do not ask for clarification, do not ask questions, and do not say goodbye or anything that would end the conversation. Keep your output to one short sentence. Always reply in English, regardless of the language of the message you received."

# Chain config. Each entry is (label, module_name). The module must expose `relay(text, system_prompt)`.
RELAYS = [
    ("relay_01_qwen",      "relay_01_qwen"),
    ("relay_02_smol",      "relay_02_smol"),
    ("relay_03_stablelm_zephyr", "relay_03_stablelm_zephyr"),
    ("relay_04_phi",       "relay_04_phi"),
    ("relay_05_stablelm",  "relay_05_stablelm"),
]

# Total number of hops the message will make through the relay pool.
CHAIN_LENGTH = 8


def _load_relays() -> dict:
    """Load all relay modules. Returns {name: (relay_fn, extra_prompt)}."""
    loaded = {}
    for name, module_name in RELAYS:
        module = import_module(module_name)
        relay_fn = getattr(module, "relay")
        extra_prompt = getattr(module, "RELAY_EXTRA_PROMPT", "")
        loaded[name] = (relay_fn, extra_prompt)
    return loaded


def _register_log_in_viewer(csv_filename: str) -> None:
    """Prepend csv_filename to the LOG_FILES array in log-viewer/app.js
    and installation/loader.js. Skips any file that does not exist."""
    targets = [
        _here.parent / "log-viewer"  / "app.js",
        _here.parent / "installation" / "loader.js",
    ]
    marker    = "const LOG_FILES = [\n"
    new_entry = f"  '{csv_filename}',\n"

    for path in targets:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if marker not in content:
            _log(f"{path.name}: LOG_FILES marker missing — skipping.")
            continue
        content = content.replace(marker, marker + new_entry, 1)
        path.write_text(content, encoding="utf-8")
        _log(f"{path.name} updated: {csv_filename} added to LOG_FILES.")


def _build_hop_sequence(relay_names: list, chain_length: int) -> list:
    """Build a hop sequence of `chain_length` relay names.
    Picks randomly with no immediate repeat."""
    if not relay_names:
        return []
    sequence = []
    last = None
    pool = relay_names if len(relay_names) > 1 else relay_names * 2
    for _ in range(chain_length):
        candidates = [r for r in pool if r != last]
        pick = random.choice(candidates)
        sequence.append(pick)
        last = pick
    return sequence


def main() -> None:
    if set_chain_length is not None:
        set_chain_length(CHAIN_LENGTH)

    if start_visuals is not None:
        start_visuals()

    # ── Load once, reuse across all runs ─────────────────────────────────────
    _log("Loading relays…")
    try:
        loaded_relays = _load_relays()
    except Exception as e:
        _log(f"Error: Failed to load relay modules. {e}")
        print(str(e), file=sys.stderr)
        if stop_visuals is not None:
            stop_visuals()
        sys.exit(1)
    _log(f"{len(RELAYS)} relay models loaded.")

    _log("Loading STT…")
    try:
        from stt import transcribe_once
    except ImportError as e:
        _log(f"Error: Failed to load STT module. {e}")
        print(str(e), file=sys.stderr)
        sys.exit(1)

    _log("Ready — press SPACE to start.")

    # ── Run loop ──────────────────────────────────────────────────────────────
    while True:

        # 1. Wait for the user to press SPACE.
        chain_length = CHAIN_LENGTH
        if wait_for_start is not None:
            result = wait_for_start()
            if result is None:      # user pressed Q before starting
                break
            chain_length = result

        hop_sequence = _build_hop_sequence([name for name, _ in RELAYS], chain_length)
        if configure_hops is not None:
            configure_hops(hop_sequence)
        _log(f"Chain: {chain_length} hops across {len(RELAYS)} models.")

        # 2. Record and transcribe.
        _log("Ready. Speak now…")
        if set_recording is not None:
            set_recording(True)
        try:
            text = transcribe_once()
        except ValueError:
            chain_log.reset()
            if reset_state is not None:
                reset_state()
            _log("No speech detected — press SPACE to try again.")
            if request_retry is not None:
                request_retry()
            continue
        except (ImportError, RuntimeError) as e:
            _log(f"Error: {e}")
            print(str(e), file=sys.stderr)
            sys.exit(1)
        finally:
            if set_recording is not None:
                set_recording(False)

        _log(f"Transcript: {text[:100]}")
        _log(f"Starting chain ({chain_length} hops)…")

        # 3. Run the relay chain.
        try:
            for hop_idx, relay_name in enumerate(hop_sequence):
                hop_id     = f"hop_{hop_idx + 1:02d}"
                next_relay = hop_sequence[hop_idx + 1] if hop_idx + 1 < len(hop_sequence) else "END"
                relay_fn, extra_prompt = loaded_relays[relay_name]
                effective_prompt = RELAY_SYSTEM_PROMPT + (" " + extra_prompt if extra_prompt else "")

                received_text = text
                if hop_start is not None:
                    hop_start(hop_id, relay_name, text)
                text = relay_fn(text, effective_prompt)
                if hop_stop is not None:
                    hop_stop(hop_id, relay_name, text, next_relay)
                chain_log.add_hop(hop_idx, relay_name, received_text, text)

        except Exception as e:
            _log(f"Error: Relay LLM failed. {e}")
            print(str(e), file=sys.stderr)
            if stop_visuals is not None:
                stop_visuals()
            sys.exit(1)

        # 4. Save and register.
        _log("Chain complete.")
        csv_path = chain_log.save_csv()
        _log(f"Saved: {csv_path.name}")
        _register_log_in_viewer(csv_path.name)

        # 5. Print prompt.
        if wait_for_print_decision is not None:
            _log("Print receipt? Press P = yes   N = no")
            if wait_for_print_decision():
                _log("Printing…")
                try:
                    from pos_printer import print_receipt
                    print_receipt(csv_path)
                    _log("Printed.")
                except Exception as e:
                    _log(f"Print failed: {e}")
            else:
                _log("Print skipped.")

        # 6. Run-again or quit prompt.
        if wait_for_next_action is not None:
            _log("R = run again   Q = quit")
            action = wait_for_next_action()
            if action == "quit":
                break
            # "reset": clear state and loop back for another run.
            chain_log.reset()
            if reset_state is not None:
                reset_state()
            _log("Ready — press SPACE to start.")
        else:
            break   # no visual layer — exit after one run

    if stop_visuals is not None:
        stop_visuals()


if __name__ == "__main__":
    main()
