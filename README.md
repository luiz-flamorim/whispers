# Whisper Chain — Whispering Game MVP

An experimentation in the whispering game: you speak into the microphone; the app transcribes your speech and runs it through a chain of LLM relays. Each relay receives the previous output and responds in its own words. This is the MVP with one speech capture step and two relays.


## Voice capture (speech-to-text)

### Configuration

- **STT (recording & Whisper):** edit `src/stt.py` — `RECORD_SECONDS`, `SAMPLE_RATE`, `INPUT_DEVICE`, `WHISPER_MODEL_SIZE`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`.
- **Relays:** edit the relay modules in `src/` — `MODEL_NAME`, `MAX_NEW_TOKENS`, `TEMPERATURE`.
- **Chain order and shared prompt:** edit `src/main.py` — `RELAY_SYSTEM_PROMPT` and the `RELAYS` list.

### Voice capture

Voice is captured and turned into text **without using an LLM**:

1. **Recording** — I use the **sounddevice** library to read from the default microphone and write a short WAV file. It’s a thin wrapper around PortAudio (cross-platform). No AI here; it’s just audio I/O.
2. **Transcription** — I use **faster-whisper** to turn that WAV into text. faster-whisper is a Python library that runs OpenAI’s Whisper model locally via CTranslate2. Whisper is a **speech-recognition model** (audio → text), not a chat/LLM. Everything runs on your machine; no cloud API is called.

**sounddevice** = capture from mic; **faster-whisper** = offline speech-to-text. The resulting text is then passed to the first relay in the chain.

- sounddevice: https://python-sounddevice.readthedocs.io/
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Whisper (OpenAI): https://github.com/openai/whisper


## Relays (LLMs)

Relays are **instruction-tuned language models** run locally with **Hugging Face Transformers**. Each relay gets the previous step’s text and a shared system prompt, and returns one reply. Order: transcript → relay 1 → relay 2 → …

### relay_01_qwen

- **Model:** Qwen2.5-3B-Instruct (Alibaba).
- **Hugging Face:** https://huggingface.co/Qwen/Qwen2.5-3B-Instruct  
- **Qwen:** https://github.com/QwenLM/Qwen2  
- **Transformers:** https://huggingface.co/docs/transformers

### relay_02_smol

- **Model:** SmolLM2-1.7B-Instruct (Hugging Face).
- **Hugging Face:** https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct  
- **Transformers:** https://huggingface.co/docs/transformers  

Ungated: no login required to download.


## Setup

From the project root (e.g. `Wishpers`):

```bash
 # Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1  
# or: source .venv/bin/activate  # macOS/Linux

pip install -r whisper_chain/requirements.txt
python whisper_chain/scripts/download_model.py   # pre-download relay models (optional but recommended)

# run
python whisper_chain/main.py
```

# Documentation

26/02/2026

First impression in running Qwen2.5-3b to SmolLM2-1.7B-Instruct
they are just passing the message from one to another, I need to add something they interpret first.
```
RELAY_SYSTEM_PROMPT = (
    "You are part of a message relay chain. "
    "Understand the message you are receiving, and with your own words, "
    "please output a text of what you have heard. "
    "please don't ask for clarification, or raise any questions. "
    "please treat this as a conversations that will stop after your output. "
    "don't say goodbye, or anything else that would end the conversation."
)
```
---