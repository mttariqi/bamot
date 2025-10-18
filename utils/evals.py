import re

def extract_numeric_answer(text: str):
    """
    Expect pattern 'ANSWER: <number>'
    Return as string normalized (strip spaces).
    """
    m = re.findall(r"ANSWER:\s*([\-]?\d+(?:\.\d+)?)", text)
    if not m:
        # Try final number fallback
        m = re.findall(r"([\-]?\d+(?:\.\d+)?)", text)
        return m[-1].strip() if m else None
    return m[-1].strip()

def is_correct(pred: str, gold: str) -> bool:
    """Simple numeric exact match (string compare after stripping)."""
    if pred is None:
        return False
    return pred.strip() == str(gold).strip()
