/* A baseball uniform painted on the mannequin in the shader, from its bind-pose (T-pose, meters, +z forward)
   coordinates: no UV layout needed. White home jersey and pants with thin pinstripes, team-color belt, socks,
   batting gloves and cleats, the number on the back and the team name on the chest. */
import * as THREE from 'three';

function textTexture(text: string, w: number, h: number, font: string, color: string, stroke?: string) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const g = c.getContext('2d');
  if (g) {
    g.clearRect(0, 0, w, h);
    g.font = font;
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    if (stroke) {
      g.lineWidth = h * 0.08;
      g.strokeStyle = stroke;
      g.strokeText(text, w / 2, h / 2);
    }
    g.fillStyle = color;
    g.fillText(text, w / 2, h / 2);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

export interface UniformLook {
  base: string; // jersey and pants
  trim: string; // pinstripes, lettering, socks
  dark: string; // belt, gloves, cleats
  skin: string;
  number: string;
  name: string;
}

export function uniformMaterial(look: UniformLook): THREE.MeshStandardMaterial {
  const m = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.68, metalness: 0 });
  const num = textTexture(look.number, 256, 256, '700 200px "Barlow Condensed", "Arial Narrow", sans-serif', look.trim, look.dark);
  const name = textTexture(look.name, 512, 160, 'italic 700 120px "Barlow Condensed", "Arial Narrow", sans-serif', look.trim, look.dark);
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, {
      uBase: { value: new THREE.Color(look.base) },
      uTrim: { value: new THREE.Color(look.trim) },
      uDark: { value: new THREE.Color(look.dark) },
      uSkin: { value: new THREE.Color(look.skin) },
      uNum: { value: num },
      uName: { value: name },
    });
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vBind;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvBind = position;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec3 vBind;
        uniform vec3 uBase; uniform vec3 uTrim; uniform vec3 uDark; uniform vec3 uSkin;
        uniform sampler2D uNum; uniform sampler2D uName;
        float hsh(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        vec3 b = vBind; float ax = abs(b.x); float y = b.y;
        vec3 col = uBase;
        // pinstripes: vertical on the body, along the arm on the sleeves (the bind pose is a T-pose)
        float stripe = ax > 0.24 ? fract(b.z * 14.0 + 0.5) : fract(b.x * 14.0 + 0.5);
        float line = smoothstep(0.0, 0.012, abs(stripe - 0.5) - 0.465);
        col = mix(col, uTrim, line * 0.7);
        // cloth weave
        col *= 0.95 + 0.06 * hsh(floor(b.xy * 900.0));
        bool head = y > 1.5 && ax < 0.13;
        bool forearm = ax > 0.47 && y > 1.32;
        bool hand = ax > 0.66 && y > 1.32;
        if (y < 0.1) col = uDark;                                    // cleats
        else if (y < 0.44) col = uTrim * 0.85;                      // socks
        else if (y > 0.92 && y < 0.99 && ax < 0.24) col = uDark;    // belt
        if (forearm) col = uSkin;
        if (hand) col = uDark;                                       // batting gloves
        if (head) col = uSkin;
        if (ax > 0.4 && ax < 0.44 && y > 1.32) col = uTrim;          // sleeve trim
        // number on the back, name across the chest
        if (b.z < -0.04 && y > 1.1 && y < 1.42 && ax < 0.15) {
          vec4 t = texture2D(uNum, vec2((b.x + 0.15) / 0.3, (y - 1.1) / 0.32));
          col = mix(col, t.rgb, t.a);
        }
        if (b.z > 0.05 && y > 1.2 && y < 1.33 && ax < 0.17) {
          vec4 t = texture2D(uName, vec2((-b.x + 0.17) / 0.34, (y - 1.2) / 0.13));
          col = mix(col, t.rgb, t.a);
        }
        diffuseColor.rgb = col;`);
  };
  m.customProgramCacheKey = () => `uniform-${look.number}-${look.name}`;
  return m;
}
