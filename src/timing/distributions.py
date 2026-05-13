from __future__ import annotations

import math
import random


class TimingDistribution:

    @staticmethod
    def gaussian(mean: float, sigma: float) -> float:
        return max(0.1, random.gauss(mean, sigma))

    @staticmethod
    def exponential(lambd: float) -> float:
        return max(0.1, random.expovariate(1.0 / lambd))

    @staticmethod
    def uniform(low: float, high: float) -> float:
        return random.uniform(low, high)

    @staticmethod
    def lognormal(mu: float, sigma: float) -> float:
        return max(0.1, random.lognormvariate(mu, sigma))

    @staticmethod
    def pareto(alpha: float, minimum: float = 0.1) -> float:
        return max(minimum, random.paretovariate(alpha) * minimum)

    @staticmethod
    def human_keystroke(wpm: float = 60.0) -> float:
        base_delay = 60.0 / (wpm * 5)
        return max(0.02, random.gauss(base_delay, base_delay * 0.3))

    @staticmethod
    def human_reaction(min_ms: float = 150, max_ms: float = 500) -> float:
        return random.uniform(min_ms, max_ms) / 1000.0

    @staticmethod
    def page_dwell_time(mean_seconds: float = 30.0) -> float:
        return max(2.0, random.lognormvariate(math.log(mean_seconds), 0.8))