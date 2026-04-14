# Whisper Chain — Whispering Game MVP

An experimentation in the whispering game: you speak into the microphone; the app transcribes your speech and runs it through a chain of LLM relays. Each relay receives the previous output and responds in its own words. This is the MVP with one speech capture step and two relays.


## Voice capture (speech-to-text)

Microphone input is recorded and transcribed locally — no LLM, no cloud. The transcript is then passed to the first relay.

<details>
<summary>How it works & configuration</summary>

- **Recording** — `sounddevice` reads from the microphone and writes a short WAV file.
- **Transcription** — `faster-whisper` runs OpenAI's Whisper model locally via CTranslate2 (audio → text).

Configure in `src/stt.py`: `RECORD_SECONDS`, `SAMPLE_RATE`, `INPUT_DEVICE`, `WHISPER_MODEL_SIZE`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`.

- sounddevice: https://python-sounddevice.readthedocs.io/
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Whisper (OpenAI): https://github.com/openai/whisper

</details>


## Relays (LLMs)

Relays are **instruction-tuned language models** run locally with **Hugging Face Transformers**. Each relay gets the previous step's text and a shared system prompt, and returns one reply. Order: transcript → relay 1 → relay 2 → …

Configure chain order and shared prompt in `src/main.py` — `RELAY_SYSTEM_PROMPT` and the `RELAYS` list.

Each relay module declares its own configuration at the top of the file:

```python
MODEL_NAME         = ""   # Hugging Face model identifier (e.g. "Qwen/Qwen2.5-3B-Instruct")
INPUT_TEXT         = ""   # Placeholder for standalone testing only — not used by the chain
MAX_NEW_TOKENS     = 0    # Maximum number of tokens the model can generate per reply
TEMPERATURE        = 0.0  # Sampling temperature: lower = more literal, higher = more creative
RELAY_EXTRA_PROMPT = ""   # Optional extra instruction appended to the shared system prompt for this relay only. Leave empty to use the shared prompt unchanged.
```

<details>
<summary>relay_01_qwen</summary>

- **Model:** Qwen2.5-3B-Instruct (Alibaba). ~3B parameters.
- **Hugging Face:** https://huggingface.co/Qwen/Qwen2.5-3B-Instruct  
- **Qwen:** https://github.com/QwenLM/Qwen2  
- **Transformers:** https://huggingface.co/docs/transformers  

Ungated; no login required. `MAX_NEW_TOKENS = 200`, `TEMPERATURE = 0.7`. `RELAY_EXTRA_PROMPT = ""` — uses the shared system prompt unchanged.
</details>

<details>
<summary>relay_02_smol</summary>

- **Model:** SmolLM2-1.7B-Instruct (Hugging Face). ~1.7B parameters.
- **Hugging Face:** https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct  
- **Transformers:** https://huggingface.co/docs/transformers  

Ungated; no login required. `MAX_NEW_TOKENS = 200`, `TEMPERATURE = 0.7`. `RELAY_EXTRA_PROMPT = ""` — uses the shared system prompt unchanged.
</details>

<details>
<summary>relay_03_tinyllama</summary>

- **Model:** TinyLlama-1.1B-Chat-v1.0 (TinyLlama). ~1.1B parameters.
- **Hugging Face:** https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0  
- **Transformers:** https://huggingface.co/docs/transformers  

Ungated (Apache 2.0); no login required. `MAX_NEW_TOKENS = 60`, `TEMPERATURE = 0.4` — constrained to prevent the model from wandering off-topic. `RELAY_EXTRA_PROMPT` adds a stronger instruction: *"You are passing on a message, not answering it. Output only a single sentence that captures what was said."*
</details>

<details>
<summary>relay_04_phi</summary>

- **Model:** Phi-3-mini-4k-instruct (Microsoft). ~3.8B parameters.
- **Hugging Face:** https://huggingface.co/microsoft/Phi-3-mini-4k-instruct  
- **Transformers:** https://huggingface.co/docs/transformers  

Ungated (MIT licence); no login required. `MAX_NEW_TOKENS = 200`, `TEMPERATURE = 0.7`. `RELAY_EXTRA_PROMPT = ""`. Strong instruction-following at small scale — keeps relay fidelity high while introducing a distinct linguistic style.
</details>

<details>
<summary>relay_05_opt</summary>

- **Model:** OPT-1.3B (Meta). ~1.3B parameters.
- **Hugging Face:** https://huggingface.co/facebook/opt-1.3b  
- **Transformers:** https://huggingface.co/docs/transformers  

Ungated (OPT licence); no login required. `MAX_NEW_TOKENS = 80`, `TEMPERATURE = 0.9`. `RELAY_EXTRA_PROMPT = ""`. Older decoder-only architecture with no chat-template support — uses a plain prompt string rather than `apply_chat_template`. Higher temperature and shorter output window maximise linguistic drift, making it the most unpredictable relay in the pool.
</details>


## Setup

From the project root (e.g. `whisper_chain`):

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1  
# or: source .venv/bin/activate  # macOS/Linux

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/download_model.py   # pre-download relay models (optional but recommended)

# run
python src/main.py
```

# Rebuilding the Environment
Unfortunately often Python and Windows don't get along, this means that sometimes the app decides to throw errors beyond my knowledge. The best option I hjave found to sort it is to delete the environment and recreate it fresh installing the dependencies. Here is my method:
1. Delete .venv fully (Explorer manual delete is fine).
2. Close IDE + terminals.
3. Reboot (to clear file locks).
4. Reopen terminal in repo root.
5. Recreate the environment with 3.11, upgrade pip and reinstall dependencies

```bash
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

# Journal

Click to expand and see details.

<details>

<summary>26/03/2026: Two new relays added; configurable chain length; visual polish.</summary>

Added `relay_04_phi` (Microsoft Phi-3-mini-4k-instruct, ~3.8B) and `relay_05_opt` (Meta OPT-1.3B) to the relay pool. OPT has no chat-template support, so its module uses a plain prompt string — this also makes it the most architecturally distinct relay in the chain, useful for maximising drift.

Introduced `CHAIN_LENGTH` in `main.py` (default 5, freely adjustable). A `_build_hop_sequence` function draws that many relays randomly from the pool with no immediate repeats, assigns each a `hop_id` (`hop_01`, `hop_02`, …), and feeds the sequence to `visual_state`. The chain is now independent of the number of relay files — you can run 12 hops with 5 models, or 3 hops with 2.

Visual fixes: separator lines were overlapping text — increased clearance above and below each divider. Added `mouse_wheel` callback so the window scrolls with the mouse wheel; auto-scroll (following the active hop) resumes automatically ~3 seconds after the last manual scroll.

</details>

<details>

<summary>26/03/2026: Visual layer refactored; startup sequence optimised; architecture modularised.</summary>

Redesigned the visual layer into three separate modules with clear responsibilities: `visual_state.py` (thread-safe shared state), `visuals.py` (pure renderer), and the existing `main.py` (orchestrator). This eliminates the previous single-context issue where `py5canvas.run()` would reload the module and lose all state updates, causing columns to never appear.

Moved all heavy imports (`stt`, relay modules) to lazy load inside `main()` after the visual window is already open. This means the window is visible and responsive while models load in the background. Startup sequence is now: open window → load relays → load STT → speak.

The relay chain in `RELAYS` is now defined as module names (strings) rather than imported functions, making per-machine configuration cleaner — each node only imports the relay module it needs.

Added clean shutdown: pressing `q` or `Esc` in the visual window closes it and exits Python. Window stays open after relay completion so results can be reviewed.

</details>

<details>

<summary>05/03/2026: Greeting-handling in prompt; TinyLlama limited to 30 tokens; language drift noted.</summary>
I have noticed that when the LLM is greeted with "Hello" or something else, it tends to responde to the greeting rather than understand and pass the message. I am adding details to the prompt to prevent it. I am also limiting the number of tokens from Tiny Llama to 30. I have notice a language switch when reducing the tokens from Llama, which needs to be fixed.

```bash
RELAY_SYSTEM_PROMPT = (
    "You are part of a message relay chain. Your only job is to understand what was said and, in your own words, output a short rephrase of that message for the next relay. Do not reply to the message as if in a conversation—only pass it on. If the message is a greeting (e.g. 'Hello'), a thanks, or another short phrase, still pass it as content (e.g. 'Someone said hello'). Do not ask for clarification, do not ask questions, and do not say goodbye or anything that would end the conversation. Keep your output to one short sentence when possible. Reply in the same language as the message you received"
)
```

```bash
### TRANSCRIPT: Yeah, yeah, yeah, yeah, yeah. So, what is this art of art? Things about like projection.
### relay_01_qwen: Projection seems to be discussed, along with other aspects of artistry.
### relay_02_smol: "Artist is discussing projection techniques in a project."
### relay_03_tinyllama: "Il artista è discutendo i metodi di prospettiva nelle opere di realizzazione."
```
</details>

<details>
<summary>02/03/2026: Prompt amended; TinyLlama added as third relay.</summary>

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
</details>

<details>
<summary>26/02/2026: First run Qwen-SmolLM; prompt updated so relays interpret rather than just pass.</summary>

First impression in running Qwen2.5-3b to SmolLM2-1.7B-Instruct
they are just passing the message from one to another, I need to add something they interpret first.

```bash
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
</details>
