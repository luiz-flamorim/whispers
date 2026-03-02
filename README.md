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

### relay_03_tinyllama

- **Model:** TinyLlama-1.1B-Chat-v1.0 (TinyLlama).
- **Hugging Face:** https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0  
- **Transformers:** https://huggingface.co/docs/transformers  

Ungated (Apache 2.0); no login required. ~1.1B parameters, good as a third hop to keep the chain light.


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

# Journal

### 02/03/2026

Amended the prompt and added tinyLlama
```bash
RELAY_SYSTEM_PROMPT = (
    "You are part of a message relay chain. "
    "Understand the message you are receiving, and with your own words, output a text of what you have heard."
    "please don't ask for clarification, or raise any questions. "
    "don't say goodbye, or anything else that would end the conversation."
)
```
```
TRANSCRIPT:
I would like to know more about Maths
### relay_01_qwen: Claro, eu também gosto de matemática. Gostaria de saber se você tem um tópico específico em mente para explorar ou se você quer uma introdução geral à matemática?
### relay_02_smol: Sure, I also like mathematics. Would you like to know if they have a specific topic in mind to explore or if they want a general introduction to mathematics?
### relay_03_tinyllama: I don't have access to the specific topic or intent of the person you're asking about. However, in general, if they have a specific topic in mind, you can ask them about it and provide a brief explanation or example. If they're interested in a general introduction to mathematics, you could start by asking them if they have any specific questions or areas they're interested in learning more about. Then, you can provide a brief overview of what mathematics is and how it's used in everyday life.
```

### 26/02/2026

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