// Pure analysis helpers (tested). No DOM/WebAudio — works in Node via ffmpeg-decoded PCM.

/** RMS energy per hop. samples: Float32Array mono. hops: number of output buckets. */
export function rmsEnvelope(samples, hops) {
  const out = new Float32Array(hops);
  const win = Math.floor(samples.length / hops);
  for (let h = 0; h < hops; h++) {
    let sum = 0;
    const start = h * win;
    for (let i = 0; i < win; i++) { const v = samples[start + i] || 0; sum += v * v; }
    out[h] = Math.sqrt(sum / win);
  }
  return out;
}

/** Scale array so min->0, max->1. Flat input -> all zeros. */
export function normalize(arr) {
  let min = Infinity, max = -Infinity;
  for (const v of arr) { if (v < min) min = v; if (v > max) max = v; }
  const range = max - min;
  return arr.map(v => (range === 0 ? 0 : (v - min) / range));
}

/** Indices where the normalized envelope crosses `threshold` (up or down). */
export function detectBoundaries(env, threshold) {
  const b = [];
  for (let i = 1; i < env.length; i++) {
    const a = env[i - 1] >= threshold, c = env[i] >= threshold;
    if (a !== c) b.push(i);
  }
  return b;
}

/** Simple bass-band onset (kick) detector: one-pole low-pass to isolate the
 * kick/bass band, then peak-pick local maxima in the envelope's positive
 * derivative (flux) above `floor`, debounced by `minGapSec` so closely-spaced
 * hits don't over-trigger. Returns onset times in seconds with a strength. */
export function detectOnsets(samples, sampleRate, { cutoffHz = 150, hopsPerSecond = 100, minGapSec = 0.08, floor = 0.35 } = {}) {
  const rc = 1 / (2 * Math.PI * cutoffHz);
  const dt = 1 / sampleRate;
  const alpha = dt / (rc + dt);
  const lp = new Float32Array(samples.length);
  let prev = 0;
  for (let i = 0; i < samples.length; i++) { prev = prev + alpha * (samples[i] - prev); lp[i] = prev; }

  const hops = Math.max(1, Math.round((samples.length / sampleRate) * hopsPerSecond));
  const env = normalize(Array.from(rmsEnvelope(lp, hops)));
  const flux = env.map((v, i) => Math.max(0, v - (env[i - 1] ?? v)));

  const onsets = [];
  let lastT = -Infinity;
  for (let i = 1; i < flux.length - 1; i++) {
    const t = i / hopsPerSecond;
    if (flux[i] < floor) continue;
    if (flux[i] < flux[i - 1] || flux[i] < flux[i + 1]) continue; // local peak only
    if (t - lastT < minGapSec) continue;                          // debounce
    onsets.push({ t: +t.toFixed(3), strength: +flux[i].toFixed(3) });
    lastT = t;
  }
  return onsets;
}
