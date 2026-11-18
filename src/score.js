/** Piecewise-linear sample of [{t,v},...] sorted by t. Clamps outside the range. */
export function sampleCurve(points, t) {
  if (points.length === 0) return 0;
  if (t <= points[0].t) return points[0].v;
  const last = points[points.length - 1];
  if (t >= last.t) return last.v;
  for (let i = 1; i < points.length; i++) {
    if (t <= points[i].t) {
      const a = points[i - 1], b = points[i];
      const f = (t - a.t) / (b.t - a.t);
      return a.v + (b.v - a.v) * f;
    }
  }
  return last.v;
}

/** Sample the wake curve at time t, returning 0..1 progress. */
export function sampleScore(score, t) {
  return sampleCurve(score.wake, t);
}
