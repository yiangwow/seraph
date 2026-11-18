"""The dormant->awake wake curve, ported from src/score-data.js's `wake` array.
If that curve is ever re-authored (e.g. against a different/trimmed track),
update both files in the same commit — this is a manual mirror, not a shared
data file, by deliberate simplication (see plan Task 2 for rationale)."""

WAKE_CURVE = [
    (0.0, 0.00),
    (8.0, 0.04),
    (15.5, 0.10),
    (16.4, 0.22),
    (20.0, 0.38),
    (24.0, 0.50),
    (32.0, 0.58),
    (42.4, 0.62),
    (43.2, 0.70),
    (47.9, 0.72),
    (48.8, 0.78),
    (53.4, 0.79),
    (54.2, 0.85),
    (60.3, 0.86),
    (62.1, 0.91),
    (71.9, 0.92),
    (74.9, 0.96),
    (78.1, 0.97),
    (79.0, 1.00),
    (90.0, 1.00),
]


def sample_wake(t):
    """Piecewise-linear sample of WAKE_CURVE at time t (seconds). Clamps
    outside the curve's range — mirrors src/score.js's sampleCurve exactly."""
    pts = WAKE_CURVE
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        t1, v1 = pts[i]
        if t <= t1:
            t0, v0 = pts[i - 1]
            f = (t - t0) / (t1 - t0)
            return v0 + (v1 - v0) * f
    return pts[-1][1]


# Cumulative integral of the wake curve at each knot, so wake_integral is a
# cheap closed-form lookup. Spin angles must use this (see v2 plan Task 1):
# angle = speed * (floor*t + (1-floor)*wake_integral(t)). Differentiating
# gives speed*mix(floor,1,wake(t)) exactly — smooth, monotonic, no spikes —
# unlike angle = t*speed*mix(...), whose derivative has a t*wake'(t) term
# that spikes at every curve kink.
_CUM = [0.0]
for _i in range(1, len(WAKE_CURVE)):
    _t0, _v0 = WAKE_CURVE[_i - 1]
    _t1, _v1 = WAKE_CURVE[_i]
    _CUM.append(_CUM[-1] + (_v0 + _v1) * 0.5 * (_t1 - _t0))


def wake_integral(t):
    """Integral of sample_wake from 0 to t (closed form)."""
    pts = WAKE_CURVE
    if t <= pts[0][0]:
        return pts[0][1] * t  # before first knot the curve clamps to v0
    if t >= pts[-1][0]:
        return _CUM[-1] + pts[-1][1] * (t - pts[-1][0])
    for i in range(1, len(pts)):
        t1, v1 = pts[i]
        if t <= t1:
            t0, v0 = pts[i - 1]
            f = (t - t0) / (t1 - t0)
            v_t = v0 + (v1 - v0) * f
            return _CUM[i - 1] + (v0 + v_t) * 0.5 * (t - t0)
    return _CUM[-1]
