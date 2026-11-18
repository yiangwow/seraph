import { describe, it, expect } from 'vitest';
import { rmsEnvelope, normalize, detectBoundaries, detectOnsets } from '../src/dev/analyze.js';

describe('rmsEnvelope', () => {
  it('downsamples to the requested number of hops', () => {
    const samples = new Float32Array(1000).fill(0.5);
    const env = rmsEnvelope(samples, 10);
    expect(env.length).toBe(10);
    expect(env[0]).toBeCloseTo(0.5, 5);
  });
  it('returns higher values for louder windows', () => {
    const s = new Float32Array(200);
    s.fill(0.1, 0, 100); s.fill(0.9, 100, 200);
    const env = rmsEnvelope(s, 2);
    expect(env[1]).toBeGreaterThan(env[0]);
  });
});

describe('normalize', () => {
  it('scales the peak to 1 and floor to 0', () => {
    const out = normalize([2, 4, 6]);
    expect(out[0]).toBeCloseTo(0); expect(out[2]).toBeCloseTo(1);
  });
  it('handles a flat array without NaN', () => {
    expect(normalize([3, 3, 3]).every(v => v === 0)).toBe(true);
  });
});

describe('detectBoundaries', () => {
  it('finds the index where energy jumps up past the threshold', () => {
    const env = [0.1, 0.1, 0.1, 0.9, 0.9, 0.2];
    const b = detectBoundaries(env, 0.4);
    expect(b).toContain(3); // jump up
    expect(b).toContain(5); // drop down
  });
});

describe('detectOnsets', () => {
  it('finds sharp low-frequency pulses and ignores flat sections', () => {
    const sr = 2000, dur = 3;
    const samples = new Float32Array(sr * dur);
    const at = (t) => Math.round(t * sr);
    for (let k = 0; k < 8; k++) { samples[at(1.0) + k] = 1.0; samples[at(2.0) + k] = 1.0; }
    const onsets = detectOnsets(samples, sr, { cutoffHz: 150, hopsPerSecond: 100, minGapSec: 0.08, floor: 0.2 });
    expect(onsets.length).toBeGreaterThanOrEqual(2);
    const times = onsets.map(o => o.t);
    expect(times.some(t => Math.abs(t - 1.0) < 0.1)).toBe(true);
    expect(times.some(t => Math.abs(t - 2.0) < 0.1)).toBe(true);
  });
  it('debounces closely-spaced peaks within minGapSec', () => {
    const sr = 2000, dur = 2;
    const samples = new Float32Array(sr * dur);
    const at = (t) => Math.round(t * sr);
    for (let k = 0; k < 8; k++) { samples[at(1.00) + k] = 1.0; samples[at(1.02) + k] = 1.0; }
    const onsets = detectOnsets(samples, sr, { cutoffHz: 150, hopsPerSecond: 100, minGapSec: 0.08, floor: 0.2 });
    expect(onsets.length).toBe(1);
  });
});
