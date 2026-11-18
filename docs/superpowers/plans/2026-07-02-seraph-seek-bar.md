# seraph — Seek Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a draggable timeline seek bar to the shipped piece (not just the
dev-only scrubber) so the user can skip ahead in the ~90s track while watching,
per direct user request.

**Architecture:** A small HUD-styled `<input type="range">` in `src/main.js`,
built the same way the existing volume slider already is (a `div` created and
appended in JS, not in `index.html`, styled inline to match). It reads/writes
`clock.time`/`clock.seek()` — the same audio-clock interface every other
control already uses — so no new abstractions are introduced. Distinct from
`src/dev/scrubber.js` (which stays dev-only, keeps its raw JSON curve editor,
and is stripped from production builds) — this is a minimal, user-facing
control with no editing capability, shipped in the real build.

**Tech Stack:** Same as the rest of the project (vanilla JS, no framework).

## Global Constraints

- Git authorship for every commit: the owner's git identity, no
  Co-Authored-By line.
- Do not push to any remote or create the public repo.
- The seek bar must be hidden during `SHOOT` mode (`?shoot=1`), same as the
  gate and volume control, so it doesn't appear in verification screenshots.
- Dragging the seek bar must not fight with the periodic UI-refresh loop (a
  common scrubber bug: the readout snaps the slider back to the playhead
  position while the user is still dragging it).

---

### Task 1: Add the seek bar

**Files:**
- Modify: `src/main.js`

**Interfaces:**
- Consumes: `clock.time`, `clock.duration`, `clock.seek(t)` (existing
  `audioClock.js` interface, already used by the volume control's neighbors and
  the render loop).
- Produces: no new exported interface — leaf UI addition.

- [ ] **Step 1: Add the seek bar after the volume control block**

In `src/main.js`, find this block:

```js
volSlider.addEventListener('input', () => {
  audioEl.volume = +volSlider.value;
  localStorage.setItem('seraph-vol', volSlider.value);
});

const gate = document.getElementById('gate');
```

Insert the following between them (right after the `volSlider` listener,
right before `const gate = ...`):

```js
// timeline: a slim seek bar along the bottom, lets the viewer skip ahead.
// Distinct from the dev-only scrubber (src/dev/scrubber.js) — this ships in
// the real build, with no curve-editing capability.
const seekbar = document.createElement('div');
seekbar.id = 'seekbar';
seekbar.style.cssText = 'position:fixed;left:24px;right:230px;bottom:30px;z-index:5;'
  + 'display:flex;align-items:center;gap:10px;color:#9a8666;font-size:10px;letter-spacing:2px;'
  + 'opacity:.4;transition:opacity .3s;';
seekbar.innerHTML = '<span id="seek-time">0:00</span>'
  + '<input type="range" min="0" max="1000" value="0" style="flex:1;height:2px;accent-color:#c9a869;cursor:pointer;">'
  + '<span id="seek-dur">0:00</span>';
document.body.appendChild(seekbar);
const seekSlider = seekbar.querySelector('input');
const seekTimeEl = seekbar.querySelector('#seek-time');
const seekDurEl = seekbar.querySelector('#seek-dur');
const fmtTime = (s) => `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;

let seekDragging = false;
seekSlider.addEventListener('input', () => {
  seekDragging = true;
  const d = clock.duration || 1;
  clock.seek((seekSlider.value / 1000) * d);
});
seekSlider.addEventListener('change', () => { seekDragging = false; });

setInterval(() => {
  const d = clock.duration || 1;
  if (!seekDragging) seekSlider.value = (clock.time / d) * 1000;
  seekTimeEl.textContent = fmtTime(clock.time);
  seekDurEl.textContent = fmtTime(d);
}, 100);

const gate = document.getElementById('gate');
```

- [ ] **Step 2: Hide the seek bar during SHOOT mode**

Find:
```js
if (SHOOT) { gate.style.display = 'none'; vol.style.display = 'none'; }
```
Replace with:
```js
if (SHOOT) { gate.style.display = 'none'; vol.style.display = 'none'; seekbar.style.display = 'none'; }
```

- [ ] **Step 3: Start the dev server in the background**

Run: `npm run dev`

- [ ] **Step 4: Interactively verify the seek bar works**

Write a small one-off Playwright script (or use the Bash tool directly with a
short inline Node script) that: navigates to `http://localhost:5173/` (no
`?shoot=1`, since the seek bar must be visible in the real experience), clicks
`#gate` to start playback, waits ~1s, drags/sets the `#seekbar input[type=range]`
to a value corresponding to roughly the 45s mark, waits briefly, then reads
`window.__seraph.clock.time` via `page.evaluate` to confirm it jumped to
approximately 45 (not still climbing from 0) and takes a screenshot. Expected:
`clock.time` reads close to 45 immediately after the seek (not ~1-2s, which
would mean the drag didn't actually seek). Save the screenshot to
`shots/seekbar-test.png` and view it with your Read tool to confirm the seek
bar is visible (a thin horizontal line with time readouts, bottom-left-ish,
positioned so it doesn't overlap the volume control) and the rendered scene
matches a ~45s-awake-ish state, not a ~0s-dormant state.

- [ ] **Step 5: Run the existing screenshot + selfcheck regression check**

Run: `npm run shoot -- 0 30 60 90` then
`npm run selfcheck -- shots/t_000.png shots/t_030.png shots/t_060.png shots/t_090.png`
Expected: exit 0, no warnings, confirming `?shoot=1` mode still hides all UI
(gate/vol/seekbar) and the underlying render is unaffected by this change.

- [ ] **Step 6: Stop the dev server**

- [ ] **Step 7: Commit**

```bash
git add src/main.js
git commit -m "Add a seek bar so the viewer can skip ahead in the track"
```
