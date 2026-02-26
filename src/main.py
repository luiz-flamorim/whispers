"""
Whisper Capture — Run STT then relay LLM in one chain.
"""

import sys
from pathlib import Path

# Ensure src directory is on path when run as script from any location
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from stt import transcribe_once
from relay_01_qwen import relay as relay_01_qwen
from relay_02_smol import relay as relay_02_smol

RELAY_SYSTEM_PROMPT = (
    "You are part of a message relay chain. "
    "Understand the message you are receiving, and with your own words, "
    "please output a text of what you have heard. "
    "please don't ask for clarification, or raise any questions. "
    "please treat this as a conversations that will stop after your output. "
    "don't say goodbye, or anything else that would end the conversation."
)

# Chain of (label, relay_fn); each receives (text, RELAY_SYSTEM_PROMPT).
RELAYS = [
    ("relay_01_qwen", relay_01_qwen),
    ("relay_02_smol", relay_02_smol),
]


def main() -> None:
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

    print("TRANSCRIPT:")
    print(text)

    try:
        for name, relay_fn in RELAYS:
            text = relay_fn(text, RELAY_SYSTEM_PROMPT)
            print(f"\n--- {name} OUTPUT ---")
            print(text)
    except Exception as e:
        print("Error: Relay LLM failed.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
