#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform float uTime;
uniform float uProgress;
uniform float uAspect;
// __COMMON__
void main(){
  vec2 p = (vUv - 0.5); p.x *= uAspect;
  float r = length(p);
  float wake = uProgress; // 0 = dormant, 1 = fully awake; never resets (Milestone 1 clamps this)
  vec3 col = vec3(0.01, 0.01, 0.02); // dark background

  // BURNING HALO — a ring of fire at the outer edge, flickering and never
  // resting; drawn first so wings and wheels layer in front of it. Flame
  // flicker samples noise off a direction vector, not raw angle, so there is
  // no seam at the angle wrap (unlike the eye-wheel noise, which accepts one).
  {
    float ang = atan(p.y, p.x);
    vec2 dirp = vec2(cos(ang), sin(ang));
    float rHalo = 0.56;

    // Three noise octaves — big slow tongues, mid licking wisps, fast fine
    // grain — so the edge reads as jagged, uneven flame rather than a smooth
    // wobble. Each octave runs at its own speed/frequency so the silhouette
    // never repeats or settles.
    float n1 = noise(dirp*3.5  + vec2(0.0, -uTime*0.5))  - 0.5;
    float n2 = noise(dirp*10.0 + vec2(4.0,  uTime*1.3))  - 0.5;
    float n3 = noise(dirp*26.0 + vec2(9.0,  uTime*2.6))  - 0.5;
    float lick = (n1*0.14 + n2*0.055 + n3*0.022) * mix(0.15, 1.0, wake); // barely licking dormant, wildly jagged awake

    float band = 0.020 + 0.008*n2; // narrow, flickering core so licks stay crisp
    float d = abs(r - (rHalo + lick));
    float halo = smoothstep(band, 0.0, d);

    float heat = noise(dirp*4.0 + vec2(-uTime*0.6, uTime*0.9)) * 0.7
               + noise(dirp*13.0 + vec2(2.0, -uTime*1.7)) * 0.3;
    vec3 flameCol = mix(vec3(0.55,0.10,0.02), vec3(1.0,0.45,0.08), heat);
    flameCol = mix(flameCol, vec3(1.0,0.85,0.35), smoothstep(0.72,1.0,heat));
    float flicker = 0.65 + 0.45*sin(uTime*6.5 + n3*9.0); // fast intensity flicker, never static
    col += flameCol * halo * (0.55 + 0.65*heat) * flicker * mix(0.12, 1.0, wake); // dim ember -> full blaze

    float outerGlow = smoothstep(rHalo+0.14, rHalo, r) * smoothstep(rHalo-0.03, rHalo, r);
    col += vec3(0.55,0.22,0.06) * outerGlow * 0.20 * mix(0.10, 1.0, wake);
  }

  // MANY WINGS — layered behind the wheels, breathing and folding, never resting.
  // Flat, curved, tapered strokes fanned around the core; each wing breathes
  // (length pulses) and folds (sweep angle drifts) on its own seeded clock, so
  // none of them move in unison (same independent-motion technique as the eyes).
  for (int i = 0; i < 10; i++){
    float fi = float(i);
    float baseA = fi/10.0*6.2831;
    float seed = hash(vec2(fi+41.0, 7.0));
    float foldSpeed = 0.12 + 0.10*seed;
    float foldPhase = seed*6.2831;
    float fold = mix(0.05, 0.55, wake)*sin(uTime*foldSpeed + foldPhase); // gathered in dormant, full sweep awake
    float breathe = 0.80 + 0.32*sin(uTime*(0.18+0.12*seed) + seed*4.0);

    float a = baseA + fold;
    vec2 dir = vec2(cos(a), sin(a));
    vec2 root = dir * 0.28;
    vec2 tip  = dir * (0.28 + mix(0.04, 0.32, wake)*breathe);  // folded close -> spread wide
    vec2 tangent = vec2(-dir.y, dir.x);
    float curveAmt = 0.05 + 0.09*seed;                         // each wing's own sweep character
    tip += tangent * (curveAmt + 0.04*sin(uTime*foldSpeed*1.7 + foldPhase));

    float wing = taperedCapsule(p, root, tip, 0.011, 0.0010);   // thin, feather-like taper
    float wingM = smoothstep(0.011,0.0, wing);
    vec3 wingCol = vec3(0.30,0.22,0.16) * (0.6+0.4*breathe) * mix(0.22, 1.0, wake);
    col = mix(col, wingCol, wingM*0.6);
    col += vec3(0.35,0.24,0.15) * smoothstep(0.006,0.0,abs(wing)) * 0.15 * mix(0.22, 1.0, wake); // faint edge glow, tight to the shape so it doesn't wash out the taper
  }

  // WHEELS WITHIN WHEELS — concentric rings, each on its own slow rotation and
  // squash (a 2D stand-in for "a different axis"), interlocking around the core.
  // Counter-rotating and idling purely on uTime so the dormant angel is never
  // static, even before the wake build (uProgress) is wired in (Milestone 5).
  for (int w = 0; w < 3; w++){
    float fw = float(w);
    float rr = 0.18 + 0.10*fw;                            // ring radius, wheels within wheels
    float squash = mix(1.0, 0.55, fract(fw*0.37+0.15));   // each wheel tilted differently
    float spin = uTime*(0.16 + 0.09*fw) * mix(0.22, 1.0, wake) * ((mod(fw,2.0)<1.0)?1.0:-1.0); // lazy dormant spin -> full speed awake
    vec2 q = vec2(p.x, p.y/squash);
    float rq = length(q);
    float aq = atan(q.y, q.x) - spin;

    // the rim itself: a thin luminous band
    float rim = smoothstep(0.006,0.0, abs(rq-rr));
    col += vec3(0.55,0.45,0.30) * rim * 0.5 * mix(0.22, 1.0, wake);

    // spokes: fine radial ticks around the rim so the rotation reads clearly
    float spokeN = 24.0 + 8.0*fw;
    float spoke = smoothstep(0.985,0.994, cos(aq*spokeN));
    col += vec3(0.35,0.28,0.18) * spoke * rim * 1.4 * mix(0.22, 1.0, wake);

    // eyes riding the rim, sparse and evenly spaced — each wakes and blinks on its
    // own independent, seeded clock: mostly shut, with brief asynchronous glances.
    // Never synchronized, never fully static (Milestone 2).
    float eyeN = 6.0 + 2.0*fw;
    float cell = floor(aq/6.2831*eyeN + 0.5);
    float ca = cell/eyeN*6.2831 + spin;
    vec2 ec = vec2(cos(ca), sin(ca)*squash) * rr;
    vec2 tangent = normalize(vec2(-sin(ca)*squash, cos(ca)));
    vec2 radial  = normalize(vec2(cos(ca), sin(ca)*squash));
    vec2 lp = vec2(dot(p-ec, tangent), dot(p-ec, radial));

    float seed = hash(vec2(cell + fw*97.0, fw*13.0 + 5.0));
    float speed = 0.16 + 0.16*seed;
    float phase = seed*6.2831;
    float cyc = 0.5 + 0.5*sin(uTime*speed + phase);
    float open = smoothstep(mix(0.94,0.55,wake), mix(0.995,0.78,wake), cyc); // rare brief glances dormant -> open often, longer, awake

    float eyeD = length(lp/vec2(0.020, 0.0035 + 0.0075*open)); // lid parts as it opens
    float eyeM = smoothstep(1.0,0.7,eyeD);
    col = mix(col, vec3(0.68,0.60,0.45), eyeM*(0.8-0.2*open)); // shut lid, faint gleam
    col += vec3(0.5,0.4,0.25) * smoothstep(0.05,0.0,abs(eyeD-1.0)) * 0.3; // lid seam glow
    // amber iris glints through as the lid parts
    vec2 pup = lp / vec2(0.020, 0.0075*open + 1e-4);
    col = mix(col, vec3(0.78,0.55,0.22), smoothstep(1.0,0.5,length(pup)) * eyeM * open * mix(0.28, 1.0, wake));
  }

  // core: a dark heart at the centre where the wheels converge, breathing gently
  float core = 0.10 + (0.012+0.016*wake)*sin(uTime*1.3); // heartbeat deepens and quickens as it wakes
  col *= smoothstep(core, core+0.03, r);
  col += vec3(0.10,0.05,0.03) * smoothstep(0.16,0.0,r) * 0.6 * mix(0.28, 1.7, wake);

  o = vec4(col, 1.0);
}
