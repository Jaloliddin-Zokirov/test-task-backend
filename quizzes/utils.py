import secrets
import string
from typing import Iterable, Optional


def generate_room_code(length: int = 6, alphabet: Optional[Iterable[str]] = None) -> str:
    alphabet = alphabet or (string.ascii_uppercase + string.digits)
    return "".join(secrets.choice(list(alphabet)) for _ in range(length))


def calculate_percentage(score: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((score / total) * 100.0, 2)
