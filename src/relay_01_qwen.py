# CONFIGURATION

MODEL_NAME        = "Qwen/Qwen2.5-3B-Instruct"  # Change this to swap models
INPUT_TEXT        = "Replace this with the transcript coming from your STT module."
MAX_NEW_TOKENS    = 200
TEMPERATURE       = 0.7
RELAY_EXTRA_PROMPT = ""  # Appended to the shared system prompt. Leave empty for default behaviour.

import gc
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def relay(input_text: str, system_prompt: str) -> str:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    max_memory = None
    if torch.cuda.is_available():
        free_vram, _ = torch.cuda.mem_get_info(0)
        max_memory = {0: int(free_vram * 0.90), "cpu": "32GiB"}

    tokenizer = None
    model = None
    inputs = None
    outputs = None
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
            max_memory=max_memory,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ]

        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=TEMPERATURE,
                do_sample=True,
                pad_token_id=pad_token_id,
            )

        response = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        )
    finally:
        del inputs, outputs, model, tokenizer
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

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