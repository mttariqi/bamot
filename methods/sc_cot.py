from typing import Dict, Any, List
from collections import Counter
from utils.model_gateway import ModelGateway
from utils.evals import extract_numeric_answer

def run_item(item: Dict[str, Any], gateway: ModelGateway, cot_system: str, sc_samples: int = 5):
    preds: List[str] = []
    texts: List[str] = []
    total_prompt = 0
    total_comp = 0
    latencies = []
    for _ in range(sc_samples):
        prompt = f"{item['question']}\n\nShow your work. End with: ANSWER: <number>"
        out = gateway.chat(system_prompt=cot_system, user_prompt=prompt)
        txt = out["text"]
        texts.append(txt)
        preds.append(extract_numeric_answer(txt))
        usage = out.get("usage", {})
        total_prompt += usage.get("prompt_tokens", 0) or 0
        total_comp += usage.get("completion_tokens", 0) or 0
        lat = out.get("latency", None)
        if lat is not None:
            latencies.append(lat)
    vote = Counter([p for p in preds if p is not None]).most_common(1)
    final_pred = vote[0][0] if vote else None
    avg_latency = sum(latencies)/len(latencies) if latencies else None
    return {"text": "\n\n---\n\n".join(texts), "pred": final_pred, "usage": {"prompt_tokens": total_prompt, "completion_tokens": total_comp}, "latency": avg_latency}
