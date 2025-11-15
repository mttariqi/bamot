# sanity_test.py
from utils.evals import is_correct, bool_match, is_game24_correct

# --- numeric ---
assert is_correct("ANSWER: 42", "42")
assert is_correct(" 42 ", "ANSWER: 42")
assert not is_correct("41", "42")

# --- boolean (StrategyQA) ---
assert bool_match("YES", "yes")
assert bool_match("no.", "NO")
assert not bool_match("yes", "no")

# --- game24 ---
q = "Use 12, 7, 5, 1 with + - * / and parentheses to make 24."

# valid solutions
assert is_game24_correct("12 * (7 - 5) * 1", q)
assert is_game24_correct("EXPR: 12 * (7 - 5) * 1  ANSWER: 24", q)

# invalid: correct numbers but wrong value (42)
assert not is_game24_correct("(12 - 5) * (7 - 1)", q)
# invalid even if someone appends ANSWER tag to a wrong value
assert not is_game24_correct("(12 - 5) * (7 - 1)  ANSWER: 24", q)
# invalid: uses an extra number
assert not is_game24_correct("12 * (7 - 5) * 1 * 1", q)

print("OK")
