import common from './shaders/common.glsl?raw';
import angel from './shaders/angel.frag?raw';

const inject = (src) => src.replace('// __COMMON__', common);

export function createScenes(renderer) {
  const { compile, draw, uni } = renderer;
  const prog = compile(inject(angel));

  function frame({ uTime, uProgress, uAspect }) {
    draw(prog, (g, p) => {
      g.uniform1f(uni(p, 'uTime'), uTime);
      g.uniform1f(uni(p, 'uProgress'), uProgress);
      g.uniform1f(uni(p, 'uAspect'), uAspect);
    }, null);
  }

  return { frame };
}
