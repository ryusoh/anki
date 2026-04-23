import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GRAPH_BACKGROUND_IMAGE } from "#js/config.js";

// --- INITIAL UI ---
const loading = document.getElementById("loading");

// --- DATA LOADING ---
let data;
let historyData;
try {
  const [graphRes, historyRes] = await Promise.all([
    fetch("/graph/graph_data.json"),
    fetch("/graph/history_data.json"),
  ]);
  if (!graphRes.ok)
    throw new Error(`HTTP ${graphRes.status}: ${graphRes.statusText}`);
  data = await graphRes.json();
  if (historyRes.ok) historyData = await historyRes.json();
} catch (e) {
  loading.innerHTML = `<div style="color:#f5576c;">Failed to load graph data<br><small>${e.message}</small></div>`;
  throw e;
}

const nodeCount = data.nodes.length;
const uniqueDecks = [...new Set(data.nodes.map((n) => n.deck))];
const colorPalette = [
  "#00C7BE",
  "#32ADE6",
  "#0A84FF",
  "#5E5CE6",
  "#AF52DE",
  "#BF5AF2",
  "#FF2D55",
  "#FF375F",
  "#FF3B30",
  "#FF9500",
  "#FFCC00",
  "#8E8E93",
];
const deckColorCache = new Map();
const fallbackColor = new THREE.Color("#4facfe");
uniqueDecks.forEach((deck, i) =>
  deckColorCache.set(
    deck,
    new THREE.Color(colorPalette[i % colorPalette.length]),
  ),
);

// Build adjacency
const adjacency = new Map();
if (data.links) {
  data.links.forEach((l) => {
    const s = String(l.source).trim(),
      t = String(l.target).trim();
    if (!adjacency.has(s)) adjacency.set(s, []);
    if (!adjacency.has(t)) adjacency.set(t, []);
    adjacency.get(s).push({ target: t, weight: l.weight || 1 });
    adjacency.get(t).push({ target: s, weight: l.weight || 1 });
  });
}

// --- SCENE SETUP ---
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(
  75,
  window.innerWidth / window.innerHeight,
  0.1,
  100000,
);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

// --- SHARED BUFFERS & MAPS ---
const nodeMap = new Map();
const nodeColorMap = new Map();
const positions = new Float32Array(nodeCount * 3);

data.nodes.forEach((node, i) => {
  const idStr = String(node.id).trim();
  positions[i * 3] = node.x || (Math.random() - 0.5) * 5000;
  positions[i * 3 + 1] = node.y || (Math.random() - 0.5) * 5000;
  positions[i * 3 + 2] = node.z || (Math.random() - 0.5) * 5000;

  nodeMap.set(idStr, {
    x: positions[i * 3],
    y: positions[i * 3 + 1],
    z: positions[i * 3 + 2],
  });

  // PRE-CACHE COLORS FOR MAX SPEED
  const c = deckColorCache.get(node.deck) || fallbackColor;
  nodeColorMap.set(idStr, c);
});

// --- LAYER 1: BACKGROUND (GREY MIST - CIRCULAR) ---
const bgNodeGeom = new THREE.BufferGeometry();
bgNodeGeom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
const bgColArr = new Float32Array(nodeCount * 3).fill(0.7); // Light grey
bgNodeGeom.setAttribute("aColor", new THREE.BufferAttribute(bgColArr, 3));
const bgSizArr = new Float32Array(nodeCount).fill(12); // Small but visible
bgNodeGeom.setAttribute("aSize", new THREE.BufferAttribute(bgSizArr, 1));
const bgAlpArr = new Float32Array(nodeCount).fill(0.1); // Thinnest mist
bgNodeGeom.setAttribute("aAlpha", new THREE.BufferAttribute(bgAlpArr, 1));

const commonShaderMat = {
  uniforms: { uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) } },
  vertexShader: `
    attribute float aSize; attribute vec3 aColor; attribute float aAlpha;
    varying vec3 vColor; varying float vAlpha;
    void main() {
      vColor = aColor; vAlpha = aAlpha;
      vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
      gl_PointSize = aSize * (300.0 / -mvPos.z);
      gl_Position = projectionMatrix * mvPos;
    }
  `,
  fragmentShader: `
    varying vec3 vColor; varying float vAlpha;
    void main() {
      if (length(gl_PointCoord - 0.5) > 0.5) discard;
      gl_FragColor = vec4(vColor * vAlpha, vAlpha);
    }
  `,
  transparent: true,
  depthWrite: false,
};

const bgNodes = new THREE.Points(
  bgNodeGeom,
  new THREE.ShaderMaterial(commonShaderMat),
);
scene.add(bgNodes);

// Background links (Full coverage web)
const MAX_BG_EDGES = 1500000;
const bgEdgePos = new Float32Array(MAX_BG_EDGES * 6);
let bgEdgeIdx = 0;
data.links.forEach((l, i) => {
  if (bgEdgeIdx < MAX_BG_EDGES) {
    const s = nodeMap.get(String(l.source).trim()),
      t = nodeMap.get(String(l.target).trim());
    if (s && t) {
      const o = bgEdgeIdx * 6;
      bgEdgePos[o] = s.x;
      bgEdgePos[o + 1] = s.y;
      bgEdgePos[o + 2] = s.z;
      bgEdgePos[o + 3] = t.x;
      bgEdgePos[o + 4] = t.y;
      bgEdgePos[o + 5] = t.z;
      bgEdgeIdx++;
    }
  }
});
const bgEdgeGeom = new THREE.BufferGeometry();
bgEdgeGeom.setAttribute(
  "position",
  new THREE.BufferAttribute(bgEdgePos.slice(0, bgEdgeIdx * 6), 3),
);
const bgEdgeMat = new THREE.LineBasicMaterial({
  color: 0x555555,
  transparent: true,
  opacity: 0.1,
});
const bgEdges = new THREE.LineSegments(bgEdgeGeom, bgEdgeMat);
scene.add(bgEdges);

// --- LAYER 2: HIGHLIGHTS (ALWAYS ON TOP) ---
const MAX_HI = 8000;
const hiPos = new Float32Array(MAX_HI * 3);
const hiCol = new Float32Array(MAX_HI * 3);
const hiSiz = new Float32Array(MAX_HI);
const hiGeom = new THREE.BufferGeometry();
hiGeom.setAttribute(
  "position",
  new THREE.BufferAttribute(hiPos, 3).setUsage(THREE.DynamicDrawUsage),
);
hiGeom.setAttribute(
  "aColor",
  new THREE.BufferAttribute(hiCol, 3).setUsage(THREE.DynamicDrawUsage),
);
hiGeom.setAttribute(
  "aSize",
  new THREE.BufferAttribute(hiSiz, 1).setUsage(THREE.DynamicDrawUsage),
);

const hiMat = new THREE.ShaderMaterial({
  ...commonShaderMat,
  depthTest: false,
});
// Special Z-nudge just for highlights
hiMat.vertexShader = hiMat.vertexShader.replace(
  "gl_Position = projectionMatrix * mvPos;",
  "gl_Position = projectionMatrix * mvPos; gl_Position.z -= 0.05;",
);
hiMat.fragmentShader = hiMat.fragmentShader.replace(
  "gl_FragColor = vec4(vColor * vAlpha, vAlpha);",
  "gl_FragColor = vec4(vColor, 1.0);",
);
const hiPoints = new THREE.Points(hiGeom, hiMat);
scene.add(hiPoints);

const hiEdgePos = new Float32Array(MAX_HI * 6);
const hiEdgeCol = new Float32Array(MAX_HI * 6);
const hiEdgeGeom = new THREE.BufferGeometry();
hiEdgeGeom.setAttribute(
  "position",
  new THREE.BufferAttribute(hiEdgePos, 3).setUsage(THREE.DynamicDrawUsage),
);
hiEdgeGeom.setAttribute(
  "color",
  new THREE.BufferAttribute(hiEdgeCol, 3).setUsage(THREE.DynamicDrawUsage),
);
const hiEdgeMat = new THREE.LineBasicMaterial({
  vertexColors: true,
  transparent: true,
  opacity: 1.0,
  depthTest: false,
});
const hiEdges = new THREE.LineSegments(hiEdgeGeom, hiEdgeMat);
scene.add(hiEdges);

// --- TIMELINE ACTION ---
const slider = document.getElementById("timeline-slider");
const dateDisplay = document.getElementById("date-display");

function updateTimeline() {
  if (!historyData) return;
  const dateStr = historyData.dates[parseInt(slider.value)];
  const rawActive = historyData.history[dateStr] || [];

  // FAST LOOKUP SETS
  const activeSet = new Set(rawActive.map((id) => String(id).trim()));
  const degree1 = new Set();

  activeSet.forEach((id) => {
    const neighbors = adjacency.get(id);
    if (neighbors) {
      for (let j = 0; j < neighbors.length; j++) {
        const targetId = neighbors[j].target;
        if (!activeSet.has(targetId)) degree1.add(targetId);
      }
    }
  });

  dateDisplay.innerHTML = `<div>${dateStr}</div><div>${activeSet.size}</div>`;

  // Update Highlight Nodes (Now O(1) Lookups)
  let hiIdx = 0;

  activeSet.forEach((id) => {
    if (hiIdx >= MAX_HI) return;
    const p = nodeMap.get(id);
    const c = nodeColorMap.get(id) || fallbackColor;
    if (!p) return;

    hiPos[hiIdx * 3] = p.x;
    hiPos[hiIdx * 3 + 1] = p.y;
    hiPos[hiIdx * 3 + 2] = p.z;
    hiCol[hiIdx * 3] = c.r;
    hiCol[hiIdx * 3 + 1] = c.g;
    hiCol[hiIdx * 3 + 2] = c.b;
    hiSiz[hiIdx] = 80;
    hiIdx++;
  });

  degree1.forEach((id) => {
    if (hiIdx >= MAX_HI) return;
    const p = nodeMap.get(id);
    const c = nodeColorMap.get(id) || fallbackColor;
    if (!p) return;

    hiPos[hiIdx * 3] = p.x;
    hiPos[hiIdx * 3 + 1] = p.y;
    hiPos[hiIdx * 3 + 2] = p.z;
    hiCol[hiIdx * 3] = c.r * 0.7;
    hiCol[hiIdx * 3 + 1] = c.g * 0.7;
    hiCol[hiIdx * 3 + 2] = c.b * 0.7;
    hiSiz[hiIdx] = 35;
    hiIdx++;
  });

  hiGeom.setDrawRange(0, hiIdx);
  hiGeom.attributes.position.needsUpdate = true;
  hiGeom.attributes.aColor.needsUpdate = true;
  hiGeom.attributes.aSize.needsUpdate = true;

  // Update Highlight Edges
  let hiEIdx = 0;
  activeSet.forEach((sId) => {
    (adjacency.get(sId) || []).forEach((l) => {
      if (hiEIdx >= MAX_HI) return;
      const s = nodeMap.get(sId),
        t = nodeMap.get(l.target);
      if (!s || !t) return;
      const o = hiEIdx * 6;
      hiEdgePos[o] = s.x;
      hiEdgePos[o + 1] = s.y;
      hiEdgePos[o + 2] = s.z;
      hiEdgePos[o + 3] = t.x;
      hiEdgePos[o + 4] = t.y;
      hiEdgePos[o + 5] = t.z;
      const c = deckColorCache.get(nodeDeckMap.get(sId)) || fallbackColor;
      const isHigh = activeSet.has(l.target) || degree1.has(l.target);

      let r, g, b, a;
      if (isHigh) {
        // Vivid internal links
        r = c.r;
        g = c.g;
        b = c.b;
        a = 0.8;
      } else {
        // Neutral grey outgoing links
        r = 0.4;
        g = 0.4;
        b = 0.45;
        a = 0.2;
      }

      hiEdgeCol[o] = r * a;
      hiEdgeCol[o + 1] = g * a;
      hiEdgeCol[o + 2] = b * a;
      hiEdgeCol[o + 3] = r * a;
      hiEdgeCol[o + 4] = g * a;
      hiEdgeCol[o + 5] = b * a;
      hiEIdx++;
    });
  });
  hiEdgeGeom.setDrawRange(0, hiEIdx * 2);
  hiEdgeGeom.attributes.position.needsUpdate = true;
  hiEdgeGeom.attributes.color.needsUpdate = true;
}

const nodeDeckMap = new Map();
data.nodes.forEach((n) => nodeDeckMap.set(String(n.id).trim(), n.deck));

if (historyData) {
  slider.max = historyData.dates.length - 1;
  slider.value = slider.max;
  slider.addEventListener("input", updateTimeline);
  updateTimeline(); // Initial sync happens while loading is still visible
}

// --- BOOTSTRAP ---
let maxD = 0;
for (let i = 0; i < nodeCount; i++) {
  const d = Math.sqrt(
    positions[i * 3] ** 2 +
      positions[i * 3 + 1] ** 2 +
      positions[i * 3 + 2] ** 2,
  );
  if (d > maxD) maxD = d;
}
camera.position.set(0, 0, maxD * 2.5);

const timeline = document.getElementById("timeline");

// Final Reveal - delayed slightly to ensure first frame is painted
setTimeout(() => {
  loading.style.display = "none";
  timeline.style.opacity = "1";
  timeline.style.pointerEvents = "auto";
  timeline.style.transform = "translateX(-50%) translateY(0)";
}, 200);
// --- INTERACTION & NAVIGATION ---
const keyState = {};
window.addEventListener("keydown", (e) => {
  keyState[e.key] = true;
  if (!historyData) return;
  if (e.key === "ArrowRight") {
    slider.value = Math.min(parseInt(slider.value) + 1, slider.max);
    updateTimeline();
  } else if (e.key === "ArrowLeft") {
    slider.value = Math.max(parseInt(slider.value) - 1, 0);
    updateTimeline();
  }
});
window.addEventListener("keyup", (e) => (keyState[e.key] = false));

function animate() {
  requestAnimationFrame(animate);

  // WASD Camera Move
  const speed = 25;
  const forward = new THREE.Vector3();
  camera.getWorldDirection(forward);
  const right = new THREE.Vector3()
    .crossVectors(forward, camera.up)
    .normalize();
  if (keyState["w"]) {
    camera.position.addScaledVector(camera.up, speed);
    controls.target.addScaledVector(camera.up, speed);
  }
  if (keyState["s"]) {
    camera.position.addScaledVector(camera.up, -speed);
    controls.target.addScaledVector(camera.up, -speed);
  }
  if (keyState["a"]) {
    camera.position.addScaledVector(right, -speed);
    controls.target.addScaledVector(right, -speed);
  }
  if (keyState["d"]) {
    camera.position.addScaledVector(right, speed);
    controls.target.addScaledVector(right, speed);
  }

  controls.update();
  renderer.render(scene, camera);
}
animate();
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
