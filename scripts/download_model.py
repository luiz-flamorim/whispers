"""
Pre-download all relay LLM models into the Hugging Face cache.
Run once after pip install so the first app run doesn't download GBs.

  python whisper_chain/scripts/download_model.py

Or from whisper_chain:  python scripts/download_model.py
"""

import sys
from pathlib import Path

# Project root (parent of whisper_chain) on path so we can import relays
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from whisper_chain.src.relay_01_qwen import load_model as load_model_qwen, MODEL_NAME as QWEN_MODEL
from whisper_chain.src.relay_02_smol import load_model as load_model_smol, MODEL_NAME as SMOL_MODEL


def main() -> None:
    models = [
        ("relay_01_qwen (Qwen)", QWEN_MODEL, load_model_qwen),
        ("relay_02_smol (SmolLM2)", SMOL_MODEL, load_model_smol),
    ]
    for label, model_name, load_fn in models:
        print(f"Downloading {label}: {model_name}")
        print("This may take a while. Model will be cached for future runs.")
        load_fn(model_name)
        print(f"Done. {label} is cached.\n")
    print("All models are cached.")


if __name__ == "__main__":
    main()
