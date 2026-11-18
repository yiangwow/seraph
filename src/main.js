import { createRenderer } from './gl/renderer.js';
import { createScenes } from './gl/scenes.js';
import { createAudioClock } from './audioClock.js';
import { sampleScore } from './score.js';
import { score } from './score-data.js';
// Import the track as an asset so the production build inlines it as a base64
// data URI (assetsInlineLimit is set huge in vite.config) — the single-file
// dist/index.html is then fully self-contained and plays standalone.
import trackUrl from '../audio/seraph-clip.mp3';

const SHOOT = location.search.includes('shoot'); // headless screenshot mode

const audioEl = document.getElementById('track');
audioEl.src = trackUrl;

const canvas = document.getElementById('gl');
const dpr = Math.min(devicePixelRatio || 1, 2);
function resize(){ canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr; }
resize(); addEventListener('resize', resize);

const renderer = createRenderer(canvas);
const scenes = createScenes(renderer);
const clock = createAudioClock(audioEl);

// volume: a small HUD-styled slider, bottom-right; remembers the level
const vol = document.createElement('div');
vol.id = 'vol';
vol.style.cssText = 'position:fixed;right:28px;bottom:28px;z-index:5;display:flex;align-items:center;gap:8px;'
  + 'color:#9a8666;font-size:10px;letter-spacing:2px;opacity:.4;transition:opacity .3s;';
vol.innerHTML = '<span>VOL</span><input type="range" min="0" max="1" step="0.01" style="width:110px;height:2px;accent-color:#c9a869;cursor:pointer;">';
document.body.appendChild(vol);
const volSlider = vol.querySelector('input');
volSlider.value = localStorage.getItem('seraph-vol') ?? '1';
audioEl.volume = +volSlider.value;
volSlider.addEventListener('input', () => {
  audioEl.volume = +volSlider.value;
  localStorage.setItem('seraph-vol', volSlider.value);
});

const gate = document.getElementById('gate');
if (SHOOT) { gate.style.display = 'none'; vol.style.display = 'none'; }
gate.addEventListener('click', async () => {
  gate.style.display = 'none';
  await clock.play();
});

// Organic motion (uTime) gets its own time source so the angel keeps
// breathing after the track ends, instead of freezing into a dead frame —
// clock.time (used for uProgress) correctly stays clamped to the track's
// duration; uTime must not.
let endAt = null;
(function loop(){
  const t = clock.time;
  let animT = t;
  if (clock.duration && t >= clock.duration - 0.05 && !clock.isPlaying) {
    if (endAt === null) endAt = performance.now();
    animT = clock.duration + (performance.now() - endAt) / 1000;
  } else {
    endAt = null;
  }
  const wake = sampleScore(score, t);
  scenes.frame({ uTime: animT, uProgress: wake, uAspect: canvas.width / canvas.height });
  requestAnimationFrame(loop);
})();

// expose for the dev scrubber / screenshot tool
window.__seraph = { clock, score };

if (import.meta.env.DEV && !SHOOT) {
  const { mountScrubber } = await import('./dev/scrubber.js');
  mountScrubber({ clock, score });
}
