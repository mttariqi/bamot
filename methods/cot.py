from typing import Dict, Any
from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer

def run_item(item: Dict[str, Any], gateway: ModelGateway, cot_system: str):
    prompt = f"{item['question']}\n\nShow your work. End with: ANSWER: <number>"
    out = gateway.chat(system_prompt=cot_system, user_prompt=prompt)
    text = out["text"]
    pred = extract_numeric_answer(text)
    usage = out.get("usage", {})
    latency = out.get("latency", None)
    return {"text": text, "pred": pred, "usage": usage, "latency": latency}
