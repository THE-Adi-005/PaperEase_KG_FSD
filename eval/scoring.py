"""Scoring utilities for QA evaluation.

Provides:
- normalize / extract_numbers
- is_abstain / is_correct / evidence_hit
- bootstrap_ci
"""
import random
import re

_ABSTAIN = [
    "not found", "no information", "cannot find", "can't find", "not mentioned",
    "not available", "unable to find", "no data", "not reported",
    "do not contain", "does not contain",
]
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s.%]", " ", s)
    return " ".join(s.split())


_ABSTAIN_N = [normalize(p) for p in _ABSTAIN]


def extract_numbers(s: str) -> list[float]:
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)
    return [float(x) for x in _NUM.findall(s)]


def is_abstain(answer: str) -> bool:
    n = normalize(answer)
    return any(p in n for p in _ABSTAIN_N)


def _to_float(s: str):
    try:
        return float(s.replace("%", "").strip())
    except ValueError:
        return None


def _matches(text: str, golds) -> bool:
    nt = normalize(text)
    nums = extract_numbers(text)
    for g in golds:
        g = str(g)
        gf = _to_float(g)
        if gf is not None:
            for c in (gf, gf * 100, gf / 100):
                tol = 0.05 if abs(c) >= 1 else 0.0005
                if any(abs(a - c) <= tol for a in nums):
                    return True
        else:
            gn = normalize(g)
            if gn and gn in nt:
                return True
    return False


def is_correct(answer: str, gold_answers, answerable: bool) -> bool:
    if not answerable:
        return is_abstain(answer)
    return (not is_abstain(answer)) and _matches(answer, gold_answers)


def evidence_hit(observations_text: str, gold_answers) -> bool:
    return _matches(observations_text, gold_answers)


def bootstrap_ci(values, n: int = 2000, seed: int = 0):
    vals = [float(v) for v in values]
    if not vals:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    k = len(vals)
    means = sorted(sum(rng.choice(vals) for _ in range(k)) / k for _ in range(n))
    mean = sum(vals) / k
    low = min(means[int(0.025 * n)], mean)
    high = max(means[int(0.975 * n) - 1], mean)
    return (mean, low, high)
