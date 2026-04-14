# CONFIGURATION (EDIT HERE)

MODEL_NAME         = "facebook/opt-1.3b"  # Ungated; no HF login required
INPUT_TEXT         = "Replace this with the transcript coming from your STT module."
MAX_NEW_TOKENS     = 80
TEMPERATURE        = 0.9
RELAY_EXTRA_PROMPT = ""  # Appended to the shared system prompt. Leave empty for default behaviour.

# NOTE: OPT does not support chat templates. The relay() function uses a plain
# prompt string instead of apply_chat_template.

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_model(model_name: str):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )
    return tokenizer, model


def relay(input_text: str, system_prompt: str) -> str:
    tokenizer, model = load_model(MODEL_NAME)

    # OPT has no chat template — build a plain prompt string.
    prompt = f"{system_prompt}\n\nMessage: {input_text}\nRelay:"

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    pad_token_id = tokenizer.pad_token_id
    if pad_token_id is None:
        pad_token_id = tokenizer.eos_token_id

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            do_sample=True,
            pad_token_id=pad_token_id,
        )

    # Decode only the newly generated tokens, not the prompt.
    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True
    )

    return response.strip()


if __name__ == "__main__":
    _prompt = (
        "You are part of a message relay chain. "
        "Understand the message you are receiving, and with your own words, "
        "please output a text of what you have heard."
    )
    print("INPUT:")
    print(INPUT_TEXT)
    print("\n--- RELAY OUTPUT ---\n")
    print(relay(INPUT_TEXT, _prompt))
