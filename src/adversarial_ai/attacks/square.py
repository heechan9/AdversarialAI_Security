"""Untargeted score-only Linf Square Attack, adapted to NHWC float32.

Algorithm: Andriushchenko et al., ECCV 2020, arXiv:1912.00049.
Reference: max-andr/square-attack @ ea95eebb5aca62ec790a927b5aa985ba4e87245c.
See docs/licenses/square-attack.txt for the upstream BSD-3-Clause notice.
This adapter is not an exact reproduction of the authors' benchmark.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class SquareResult:
    adversarial: np.ndarray
    clean_predictions: np.ndarray
    predictions: np.ndarray
    queries: np.ndarray  # per image, INCLUDING its clean eligibility query
    margins: np.ndarray


def _fraction(p, iteration, budget):
    t = int(iteration / budget * 10000)
    for threshold, divisor in ((8000,512),(6000,256),(4000,128),(2000,64),
                               (1000,32),(500,16),(200,8),(50,4),(10,2)):
        if t > threshold:
            return p / divisor
    return p


def square_linf(predict, images, labels, *, epsilon=.03, max_queries=1000,
                p_init=.05, seed=2026):
    """Only calls predict(NHWC)->finite scores[N,K]; never reads gradients.

    Uses true-class minus maximum other-class score as its objective. Scores
    may be logits or probabilities; the choice changes search trajectories.
    Misclassified clean samples are left unchanged. A zero budget is invalid;
    budget=1 or epsilon=0 performs only the clean query. Success uses argmax,
    including ties, rather than assuming a zero margin means misclassification.
    """
    x = np.asarray(images)
    y = np.asarray(labels)
    if (x.ndim != 4 or min(x.shape) < 1 or min(x.shape[1:3]) < 2
            or not np.issubdtype(x.dtype, np.floating)
            or not np.isfinite(x).all() or np.any(x < 0) or np.any(x > 1)):
        raise ValueError('expected finite nonempty NHWC floating images in [0,1]')
    if y.shape != (len(x),) or not np.issubdtype(y.dtype, np.integer):
        raise ValueError('labels must be a vector of integer class indices')
    if isinstance(epsilon, bool) or not np.isfinite(epsilon) or not 0 <= epsilon <= 1:
        raise ValueError('epsilon must be in [0,1]')
    if isinstance(max_queries, bool) or not isinstance(max_queries, int) or max_queries < 1:
        raise ValueError('max_queries must be a positive integer')
    if not np.isfinite(p_init) or not 0 < p_init <= 1:
        raise ValueError('p_init must be in (0,1]')
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError('seed must be a nonnegative integer')
    x = x.astype(np.float32, copy=True)
    rng = np.random.default_rng(seed)
    classes = None

    def query(z, targets):
        nonlocal classes
        scores = np.asarray(predict(z))
        if (scores.ndim != 2 or scores.shape[0] != len(z) or scores.shape[1] < 2
                or not np.isfinite(scores).all()):
            raise ValueError('predict returned invalid scores')
        if classes is not None and classes != scores.shape[1]:
            raise ValueError('predict changed class count')
        classes = scores.shape[1]
        if np.any(targets < 0) or np.any(targets >= classes):
            raise ValueError('label out of range')
        other = scores.astype(np.float64, copy=True)
        other[np.arange(len(z)), targets] = -np.inf
        return scores.argmax(1), scores[np.arange(len(z)), targets] - other.max(1)

    pred, margin = query(x, y)
    clean = pred.copy()
    best = x.copy()
    queries = np.ones(len(x), dtype=np.int64)
    if epsilon == 0 or max_queries == 1:
        return SquareResult(best, clean, pred, queries, margin)
    h, w, c = x.shape[1:]
    for iteration in range(max_queries - 1):
        active = np.flatnonzero(pred == y)
        if not len(active):
            break
        if iteration == 0:
            delta = rng.choice([-epsilon, epsilon], size=(len(active), 1, w, c))
            candidate = np.clip(x[active] + delta, 0, 1).astype(np.float32)
        else:
            delta = best[active] - x[active]
            side = min(max(round(np.sqrt(_fraction(p_init, iteration-1,
                            max_queries-1)*h*w)), 1), h-1, w-1)
            for j, idx in enumerate(active):
                row, col = rng.integers(h-side+1), rng.integers(w-side+1)
                patch = (slice(row,row+side), slice(col,col+side), slice(None))
                # Bounded retry avoids the upstream infinite loop at tiny eps.
                for _ in range(32):
                    change = rng.choice([-epsilon, epsilon], size=(1,1,c))
                    if not np.array_equal(np.clip(x[idx][patch]+change,0,1).astype(np.float32), best[idx][patch]):
                        break
                delta[j][patch] = change
            candidate = np.clip(x[active]+delta,0,1).astype(np.float32)
        new_pred, new_margin = query(candidate, y[active])
        queries[active] += 1
        # Always retain actual success (also handles exact score ties).
        improved = (new_margin < margin[active]) | (new_pred != y[active])
        accepted = active[improved]
        best[accepted] = candidate[improved]
        pred[accepted] = new_pred[improved]
        margin[accepted] = new_margin[improved]
    return SquareResult(best, clean, pred, queries, margin)
