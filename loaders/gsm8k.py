from typing import List, Dict

def load():
    """
    Tiny GSM8K-like subset (5 items).
    Each item: {"id": str, "question": str, "answer": str}
    """
    data: List[Dict] = [
        {"id": "gsm_001",
         "question": "Ali has 3 apples and buys 2 more packs of 4 apples each. How many apples in total?",
         "answer": "11"},
        {"id": "gsm_002",
         "question": "A class has 12 girls and 9 boys. If 5 more boys join, how many students now?",
         "answer": "26"},
        {"id": "gsm_003",
         "question": "Sara read 15 pages on Monday and 22 on Tuesday. She wants to reach 50 pages. How many pages left?",
         "answer": "13"},
        {"id": "gsm_004",
         "question": "A bus travels 40 km in 1 hour. How far in 3.5 hours?",
         "answer": "140"},
        {"id": "gsm_005",
         "question": "If a box has 6 rows with 5 chocolates each and Ali eats 7, how many remain?",
         "answer": "23"},
    ]
    return data
