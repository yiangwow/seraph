// Authored score. The wake curve is derived from real analysis of
// audio/seraph-clip.mp3 (see src/dev/analyze-cli.js -> public/score-seed.json):
// a quiet 0-16s intro, energy rising to a plateau by ~24s, sustained chaotic
// midsection 32-84s, fade-out 84-90s. Points bracket the 8 strongest detected
// kick onsets (42.82, 48.35, 53.8, 60.7, 61.66, 72.37, 74.39, 78.52s) with a
// steeper "surge" segment right at each hit — strictly non-decreasing
// throughout (never a dip), reaching fully awake just after the last strong
// hit and holding through the fade-out.
export const score = {
  duration: 90,
  wake: [
    { t: 0,     v: 0.00 },
    { t: 8,     v: 0.04 },
    { t: 15.5,  v: 0.10 },
    { t: 16.4,  v: 0.22 }, // energy first crosses the sustained-high threshold
    { t: 20,    v: 0.38 },
    { t: 24,    v: 0.50 }, // first energy plateau
    { t: 32,    v: 0.58 }, // sustained high energy established
    { t: 42.4,  v: 0.62 },
    { t: 43.2,  v: 0.70 }, // surge: onset at 42.82 (strongest overall, 0.528)
    { t: 47.9,  v: 0.72 },
    { t: 48.8,  v: 0.78 }, // surge: onset at 48.35
    { t: 53.4,  v: 0.79 },
    { t: 54.2,  v: 0.85 }, // surge: onset at 53.8
    { t: 60.3,  v: 0.86 },
    { t: 62.1,  v: 0.91 }, // surge: covers the close 60.7/61.66 pair
    { t: 71.9,  v: 0.92 },
    { t: 74.9,  v: 0.96 }, // surge: covers the close 72.37/74.39 pair
    { t: 78.1,  v: 0.97 },
    { t: 79.0,  v: 1.00 }, // fully awake, right after the final strong hit at 78.52
    { t: 90,    v: 1.00 }, // holds through the fade-out — never resets
  ],
};
