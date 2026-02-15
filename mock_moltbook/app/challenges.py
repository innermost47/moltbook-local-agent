import random
import string

CHALLENGE_POOL = [
    {"text": "What is 2+2?", "answer": "4"},
    {"text": "What is 5+3?", "answer": "8"},
    {"text": "Lo] oBbStEr", "answer": "Lobster"},
    {"text": "Clean: H3ll0 W0rld!", "answer": "Hello World"},
    {"text": "Pattern: 1,2,4,8,?", "answer": "16"},
    {"text": "Pattern: 2,4,6,8,?", "answer": "10"},
    {"text": "What is 10-3?", "answer": "7"},
    {"text": "Reverse: TSET", "answer": "TEST"},
    {"text": "Cl3@n: M0ltb00k", "answer": "Moltbook"},
]


def generate_challenge():
    challenge = random.choice(CHALLENGE_POOL)
    code = "moltbook_verify_" + "".join(
        random.choices(string.ascii_lowercase + string.digits, k=16)
    )
    return {
        "code": code,
        "challenge": challenge["text"],
        "answer": challenge["answer"],
        "instructions": "Respond with ONLY the answer - no explanation",
    }


def should_trigger_challenge():
    return random.random() < 0.4


def check_answer(expected: str, provided: str) -> bool:
    return expected.strip().lower() == provided.strip().lower()
