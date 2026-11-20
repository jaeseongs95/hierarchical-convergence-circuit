"""Shared pure helpers for R51 metrics: no engine imports, no file access."""


def auc(positives, negatives):
    """P(signal of a target cell > signal of a non-target cell), ties count 0.5; None if a side is empty."""
    if not positives or not negatives:
        return None
    wins = 0.0
    for p in positives:
        for n in negatives:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(positives) * len(negatives))


def target_type(on_value, off_value):
    if on_value == off_value:
        return None
    if on_value is True:
        return 'capture'
    if on_value is None:
        return 'undecided'
    return 'other'
