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
                               set_recording)
except ImportError:
    configure_hops    = None
    hop_start         = None
    hop_stop          = None
    _vlog             = None
    set_chain_length  = None
    wait_for_start    = None
    get_chain_length  = None
    set_recording     = None


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
    # Set the default hop count before the window opens so the UI shows it.
    if set_chain_length is not None:
        set_chain_length(CHAIN_LENGTH)

    if start_visuals is not None:
        start_visuals()

    # Wait for the user to press SPACE; they may adjust the hop count first.
    chain_length = CHAIN_LENGTH
    if wait_for_start is not None:
        chain_length = wait_for_start()

    hop_sequence = _build_hop_sequence([name for name, _ in RELAYS], chain_length)
    if configure_hops is not None:
        configure_hops(hop_sequence)

    _log("Loading relays…")
    try:
        loaded_relays = _load_relays()
    except Exception as e:
        _log(f"Error: Failed to load relay modules. {e}")
        print(str(e), file=sys.stderr)
        if stop_visuals is not None:
            stop_visuals()
        sys.exit(1)
    _log(f"Relays loaded. Chain: {chain_length} hops across {len(RELAYS)} models.")

    _log("Loading STT…")
    try:
        from stt import transcribe_once
    except ImportError as e:
        _log(f"Error: Failed to load STT module. {e}")
        print(str(e), file=sys.stderr)
        sys.exit(1)

    _log("Ready. Speak now…")
    if set_recording is not None:
        set_recording(True)
    try:
        text = transcribe_once()
    except ImportError as e:
        _log(f"Error: Missing dependency. {e}")
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        _log(f"Error: Recording failed. {e}")
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        _log(f"Error: Transcription failed. {e}")
        print(str(e), file=sys.stderr)
        sys.exit(1)
    finally:
        if set_recording is not None:
            set_recording(False)

    _log(f"Transcript: {text[:100]}")
    _log(f"Starting chain ({chain_length} hops)…")

    try:
        for hop_idx, relay_name in enumerate(hop_sequence):
            hop_id = f"hop_{hop_idx + 1:02d}"
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

    _log("Chain complete.")
    csv_path = chain_log.save_csv()
    _log(f"Saved: {csv_path.name}")
    _register_log_in_viewer(csv_path.name)

    if stop_visuals is not None:
        stop_visuals()


if __name__ == "__main__":
    main()
