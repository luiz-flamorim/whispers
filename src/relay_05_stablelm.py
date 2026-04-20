# CONFIGURATION (EDIT HERE)

MODEL_NAME         = "stabilityai/stablelm-2-1_6b-chat"  # Ungated; no HF login required
INPUT_TEXT         = "Replace this with the transcript coming from your STT module."
MAX_NEW_TOKENS     = 80
TEMPERATURE        = 0.7
RELAY_EXTRA_PROMPT = "Always write your reply in English. Output exactly one sentence. Do not ask questions. Do not switch to another language under any circumstances."


import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def relay(input_text: str, system_prompt: str) -> str:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="cuda" if torch.cuda.is_available() else "cpu",
    )

    try:
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
        del model, tokenizer
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
