import sys
import random
from importlib import import_module
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

try:
    from visual_state import configure_hops, hop_start, hop_stop
except ImportError:
    configure_hops = None
    hop_start = None
    hop_stop = None

try:
    from visuals import start_visuals, stop_visuals
except ImportError:
    start_visuals = None
    stop_visuals = None

RELAY_SYSTEM_PROMPT = "You are part of a message relay chain. Your only job is to understand what was said and, in your own words, output a short rephrase of that message for the next relay. Do not reply to the message as if in a conversation—only pass it on. If the message is a greeting (e.g. 'Hello'), a thanks, or another short phrase, still pass it as content (e.g. 'Someone said hello'). Do not ask for clarification, do not ask questions, and do not say goodbye or anything that would end the conversation. Keep your output to one short sentence when possible. Reply in the same language as the message you received"

# Chain config. Each entry is (label, module_name). The module must expose `relay(text, system_prompt)`.
RELAYS = [
    ("relay_01_qwen",      "relay_01_qwen"),
    ("relay_02_smol",      "relay_02_smol"),
    ("relay_03_tinyllama", "relay_03_tinyllama"),
    ("relay_04_phi",       "relay_04_phi"),
    ("relay_05_opt",       "relay_05_opt"),
]

# Total number of hops the message will make through the relay pool.
# Can exceed len(RELAYS) — relays are reused randomly with no immediate repeats.
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
    hop_sequence = _build_hop_sequence([name for name, _ in RELAYS], CHAIN_LENGTH)

    if configure_hops is not None:
        configure_hops(hop_sequence)
    if start_visuals is not None:
        start_visuals()

    try:
        loaded_relays = _load_relays()
    except Exception as e:
        print("Error: Failed to load relay modules.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        if stop_visuals is not None:
            stop_visuals()
        sys.exit(1)

    try:
        from stt import transcribe_once
    except ImportError as e:
        print("Error: Failed to load STT module.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print("Ready. Speak now…")
    try:
        text = transcribe_once()
    except ImportError as e:
        print("Error: Missing dependency.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print("Error: Recording failed.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print("Error: Transcription failed.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)

    try:
        for hop_idx, relay_name in enumerate(hop_sequence):
            hop_id = f"hop_{hop_idx + 1:02d}"
            next_relay = hop_sequence[hop_idx + 1] if hop_idx + 1 < len(hop_sequence) else "END"
            relay_fn, extra_prompt = loaded_relays[relay_name]
            effective_prompt = RELAY_SYSTEM_PROMPT + (" " + extra_prompt if extra_prompt else "")

            if hop_start is not None:
                hop_start(hop_id, relay_name, text)
            text = relay_fn(text, effective_prompt)
            if hop_stop is not None:
                hop_stop(hop_id, relay_name, text, next_relay)

    except Exception as e:
        print("Error: Relay LLM failed.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        if stop_visuals is not None:
            stop_visuals()
        sys.exit(1)

    if stop_visuals is not None:
        stop_visuals()


if __name__ == "__main__":
    main()
