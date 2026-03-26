import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from stt import transcribe_once
from relay_01_qwen import relay as relay_01_qwen
from relay_02_smol import relay as relay_02_smol
from relay_03_tinyllama import relay as relay_03_tinyllama
try:
    from visuals import relay_start, relay_stop, start_visuals, stop_visuals
except ImportError:
    relay_start = None
    relay_stop = None
    start_visuals = None
    stop_visuals = None

RELAY_SYSTEM_PROMPT = "You are part of a message relay chain. Your only job is to understand what was said and, in your own words, output a short rephrase of that message for the next relay. Do not reply to the message as if in a conversation—only pass it on. If the message is a greeting (e.g. 'Hello'), a thanks, or another short phrase, still pass it as content (e.g. 'Someone said hello'). Do not ask for clarification, do not ask questions, and do not say goodbye or anything that would end the conversation. Keep your output to one short sentence when possible. Reply in the same language as the message you received"

# Chain of (label, relay_fn); each receives (text, RELAY_SYSTEM_PROMPT).
RELAYS = [
    ("relay_01_qwen", relay_01_qwen),
    ("relay_02_smol", relay_02_smol),
    ("relay_03_tinyllama", relay_03_tinyllama),
]


def main() -> None:
    if start_visuals is not None:
        start_visuals()

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

    print(f"### TRANSCRIPT: {text}")

    try:
        for idx, (name, relay_fn) in enumerate(RELAYS):
            emitted_to = RELAYS[idx + 1][0] if idx + 1 < len(RELAYS) else "END"
            if relay_start is not None:
                relay_start(name, text)
            text = relay_fn(text, RELAY_SYSTEM_PROMPT)
            if relay_stop is not None:
                relay_stop(name, text, emitted_to)
            print(f"### {name}: {text}")
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
