import { describe, it, expect } from 'vitest';
import { sampleCurve, sampleScore } from '../src/score.js';

describe('sampleCurve', () => {
  const pts = [{ t: 0, v: 0 }, { t: 10, v: 1 }, { t: 20, v: 0 }];
  it('clamps before first and after last point', () => {
    expect(sampleCurve(pts, -1)).toBe(0);
    expect(sampleCurve(pts, 99)).toBe(0);
  });
  it('linearly interpolates between points', () => {
    expect(sampleCurve(pts, 5)).toBeCloseTo(0.5);
    expect(sampleCurve(pts, 15)).toBeCloseTo(0.5);
  });
  it('returns exact value at a knot', () => {
    expect(sampleCurve(pts, 10)).toBe(1);
  });
  it('handles a single-point curve as a constant', () => {
    expect(sampleCurve([{ t: 5, v: 0.7 }], 0)).toBe(0.7);
    expect(sampleCurve([{ t: 5, v: 0.7 }], 100)).toBe(0.7);
  });
});

describe('sampleScore', () => {
  it('samples the wake curve at time t and clamps at the end', () => {
    const score = { wake: [{ t: 0, v: 0 }, { t: 60, v: 1 }] };
    expect(sampleScore(score, 0)).toBe(0);
    expect(sampleScore(score, 30)).toBeCloseTo(0.5);
    expect(sampleScore(score, 60)).toBe(1);
    expect(sampleScore(score, 999)).toBe(1); // holds "fully awake", never resets
  });
});
