import math
from typing import Optional

def add(a: int, b: int = 0) -> int:
    return a + b

class MathEngine:
    def __init__(self, precision: int = 2):
        self.precision = precision

    def compute_sqrt(self, value: float) -> float:
        return round(math.sqrt(value), self.precision)
