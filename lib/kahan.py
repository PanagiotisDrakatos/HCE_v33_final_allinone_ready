class KahanSum:
    def __init__(self):
        self.sum = 0.0
        self.c = 0.0
    def add(self, x: float):
        y = x - self.c
        t = self.sum + y
        self.c = (t - self.sum) - y
        self.sum = t
    def value(self) -> float:
        return float(self.sum)
