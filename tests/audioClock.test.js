import { describe, it, expect, vi } from 'vitest';
import { createAudioClock } from '../src/audioClock.js';

function fakeMedia() {
  return { currentTime: 0, duration: 90, paused: true,
    play: vi.fn(function () { this.paused = false; return Promise.resolve(); }),
    pause: vi.fn(function () { this.paused = true; }) };
}

describe('createAudioClock', () => {
  it('reports clamped time within [0, duration]', () => {
    const m = fakeMedia(); const c = createAudioClock(m);
    m.currentTime = -5; expect(c.time).toBe(0);
    m.currentTime = 999; expect(c.time).toBe(90);
    m.currentTime = 50; expect(c.time).toBe(50);
  });
  it('play() starts the media and flips isPlaying', async () => {
    const m = fakeMedia(); const c = createAudioClock(m);
    await c.play();
    expect(m.play).toHaveBeenCalled(); expect(c.isPlaying).toBe(true);
  });
  it('seek() sets currentTime clamped', () => {
    const m = fakeMedia(); const c = createAudioClock(m);
    c.seek(200); expect(m.currentTime).toBe(90);
    c.seek(30); expect(m.currentTime).toBe(30);
  });
});
