import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GRAPH_BACKGROUND_IMAGE } from "#js/config.js";

// --- INITIAL UI ---
const loading = document.getElementById("loading");

// --- DATA LOADING ---
let data;
let historyData;
try {
  let graphUrl = "/graph/graph_data.json";
  let historyUrl = "/graph/history_data.json";
  const R2_DOMAIN = "https://anki-graph.lyeutsaon.com";

  // First check if private data exists, otherwise fallback to public R2
  const privateGraph = await fetch(graphUrl, { method: "HEAD" });
  if (!privateGraph.ok) {
    graphUrl = `${R2_DOMAIN}/graph/graph_data_public.json`;
    historyUrl = `${R2_DOMAIN}/graph/history_data_public.json`;
    console.log("🌐 Loading Public Anonymized Data from R2");
  }

  const [graphRes, historyRes] = await Promise.all([
    fetch(graphUrl),
    fetch(historyUrl),
  ]);
  if (!graphRes.ok)
    throw new Error(`HTTP ${graphRes.status}: ${graphRes.statusText}`);
  data = await graphRes.json();

  // Map short keys if public data is detected
  if (data.nodes && data.nodes.length > 0 && data.nodes[0].l !== undefined) {
    data.nodes = data.nodes.map((n) => ({
      id: n.id,
      label: n.l,
      deck: n.d,
      pagerank: n.p,
      size: n.s,
      x: n.x,
      y: n.y,
      z: n.z,
    }));
    data.links = data.links.map((l) => ({
      source: l.s,
      target: l.t,
      weight: l.w,
    }));
  }

  if (historyRes.ok) historyData = await historyRes.json();
} catch (e) {
  loading.innerHTML = `<div style="color:#f5576c;">Failed to load graph data<br><small>${e.message}</small></div>`;
  throw e;
}

const nodeCount = data.nodes.length;
const uniqueDecks = [...new Set(data.nodes.map((n) => n.deck))];
const deckColorCache = new Map();
const fallbackColor = new THREE.Color("#4facfe");

// GOLDEN RATIO COLOR GENERATION (MAXIMUM PERCEPTUAL DISTANCE)
const goldenRatioConjugate = 0.618033988749895;
let hue = Math.random(); // Start at a random point
uniqueDecks.forEach((deck) => {
  hue += goldenRatioConjugate;
  hue %= 1;
  const color = new THREE.Color().setHSL(hue, 0.9, 0.6);
  deckColorCache.set(deck, color);
});

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

// IMPLEMENT BACKGROUND IMAGE Support
if (GRAPH_BACKGROUND_IMAGE && GRAPH_BACKGROUND_IMAGE.enabled) {
  const loader = new THREE.TextureLoader();
  const bgPath =
    GRAPH_BACKGROUND_IMAGE.path || "/assets/backgrounds/graph_background.jpg";
  loader.load(
    bgPath,
    (texture) => {
      texture.encoding = THREE.sRGBEncoding;
      scene.background = texture;
      console.log("Graph Background Loaded:", bgPath);
    },
    undefined,
    (err) => {
      console.warn("Could not load background image:", bgPath, err);
    },
  );
} else {
  scene.background = new THREE.Color(0x0a0a0f);
}

const camera = new THREE.PerspectiveCamera(
  75,
  window.innerWidth / window.innerHeight,
  0.1,
  100000,
);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.autoRotate = false;
controls.autoRotateSpeed = 0.5;
controls.minDistance = 10;
controls.maxDistance = 100000;

let isRotating = false;
renderer.domElement.addEventListener("dblclick", () => {
  isRotating = !isRotating;
  controls.autoRotate = isRotating;
  console.log("Graph Rotation:", isRotating ? "Resumed" : "Stopped");
});

// --- SHARED BUFFERS & MAPS ---
const nodeMap = new Map();
const nodeColorMap = new Map();
const positions = new Float32Array(nodeCount * 3);
const layoutScale = 0.5; // Controls how much HUBS are pulled together

// 1. First Pass: Calculate Hub Centroids
const deckCentroids = new Map();
const deckCounts = new Map();
uniqueDecks.forEach((d) => deckCentroids.set(d, new THREE.Vector3(0, 0, 0)));
data.nodes.forEach((n) => {
  const c = deckCentroids.get(n.deck);
  c.x += n.x || 0;
  c.y += n.y || 0;
  c.z += n.z || 0;
  deckCounts.set(n.deck, (deckCounts.get(n.deck) || 0) + 1);
});
uniqueDecks.forEach((d) => {
  const count = deckCounts.get(d) || 1;
  deckCentroids.get(d).divideScalar(count);
});

// 2. Second Pass: Apply Hub Gravity (Compress space between clusters)
data.nodes.forEach((node, i) => {
  const idStr = String(node.id).trim();
  const centroid = deckCentroids.get(node.deck);

  // New Position = (Hub scaled toward zero) + (Node's local offset from Hub)
  const x = (node.x || 0) - centroid.x;
  const y = (node.y || 0) - centroid.y;
  const z = (node.z || 0) - centroid.z;

  positions[i * 3] = centroid.x * layoutScale + x;
  positions[i * 3 + 1] = centroid.y * layoutScale + y;
  positions[i * 3 + 2] = centroid.z * layoutScale + z;

  nodeMap.set(idStr, {
    x: positions[i * 3],
    y: positions[i * 3 + 1],
    z: positions[i * 3 + 2],
    size: node.s || node.size || 1,
  });

  // PRE-CACHE COLORS FOR MAX SPEED
  const c = deckColorCache.get(node.deck) || fallbackColor;
  nodeColorMap.set(idStr, c);
});

const nodeDeckMap = new Map();
data.nodes.forEach((n) => nodeDeckMap.set(String(n.id).trim(), n.deck));

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
      gl_PointSize = aSize * (150.0 / -mvPos.z);
      gl_Position = projectionMatrix * mvPos;
    }
  `,
  fragmentShader: `
    varying vec3 vColor; varying float vAlpha;
    void main() {
      float r = length(gl_PointCoord - 0.5);
      if (r > 0.5) discard;
      // Radiant Core + Soft Bloom Aura
      float bloom = pow(max(0.0, 1.0 - r * 2.0), 3.0);
      float core = smoothstep(0.5, 0.4, r);
      vec3 finalColor = vColor + (vColor * bloom * 0.6);
      gl_FragColor = vec4(finalColor * vAlpha, vAlpha * (core + bloom * 0.3));
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

// Background links (Strategic Subsampling)
const MAX_BG_EDGES = 800000;
const bgEdgePos = new Float32Array(MAX_BG_EDGES * 6);
let bgEdgeIdx = 0;
data.links.forEach((l) => {
  if (bgEdgeIdx >= MAX_BG_EDGES) return;

  const sId = String(l.source).trim();
  const tId = String(l.target).trim();

  // Selective Subsampling:
  // Show 20% of internal cluster links, but only 5% of cross-cluster noise
  const sDeck = nodeDeckMap.get(sId);
  const tDeck = nodeDeckMap.get(tId);
  const isSameDeck = sDeck && tDeck && sDeck === tDeck;
  const prob = isSameDeck ? 0.2 : 0.05;
  if (Math.random() > prob) return;

  const s = nodeMap.get(sId),
    t = nodeMap.get(tId);
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
});
const bgEdgeGeom = new THREE.BufferGeometry();
bgEdgeGeom.setAttribute(
  "position",
  new THREE.BufferAttribute(bgEdgePos.slice(0, bgEdgeIdx * 6), 3),
);
const bgEdgeMat = new THREE.LineBasicMaterial({
  color: 0x555555,
  transparent: true,
  opacity: 0.08,
  depthWrite: false,
});
const bgEdges = new THREE.LineSegments(bgEdgeGeom, bgEdgeMat);
scene.add(bgEdges);

// --- LAYER 2: HIGHLIGHTS (ALWAYS ON TOP) ---
const MAX_HI = 8000;
const hiPos = new Float32Array(MAX_HI * 3);
const hiCol = new Float32Array(MAX_HI * 3);
const hiSiz = new Float32Array(MAX_HI);
const hiAlp = new Float32Array(MAX_HI);
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
hiGeom.setAttribute(
  "aAlpha",
  new THREE.BufferAttribute(hiAlp, 1).setUsage(THREE.DynamicDrawUsage),
);

const hiMat = new THREE.ShaderMaterial({
  uniforms: {
    uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
    uTime: { value: 0 },
  },
  vertexShader: `
    attribute float aSize; attribute vec3 aColor; attribute float aAlpha;
    varying vec3 vColor; varying float vAlpha;
    void main() {
      vColor = aColor; vAlpha = aAlpha;
      vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
      gl_PointSize = aSize * (150.0 / -mvPos.z);
      gl_Position = projectionMatrix * mvPos;
      gl_Position.z -= 0.1; // Ensure top layer
    }
  `,
  fragmentShader: `
    varying vec3 vColor; varying float vAlpha;
    uniform float uTime;
    void main() {
      float r = length(gl_PointCoord - 0.5);
      if (r > 0.5) discard;
      float glow = pow(1.0 - r * 2.0, 3.0);
      float pulse = 0.9 + 0.1 * sin(uTime * 5.0);
      vec3 finalColor = vColor * (1.0 + glow * 2.0 * pulse);
      gl_FragColor = vec4(finalColor * vAlpha, vAlpha * (smoothstep(0.5, 0.3, r) + glow * 0.5));
    }
  `,
  transparent: true,
  blending: THREE.AdditiveBlending,
  depthTest: false,
});
const hiPoints = new THREE.Points(hiGeom, hiMat);
scene.add(hiPoints);

const hiEdgePos = new Float32Array(MAX_HI * 6);
const hiEdgeCol = new Float32Array(MAX_HI * 6);
const hiEdgeAlp = new Float32Array(MAX_HI * 2);
const hiEdgeGeom = new THREE.BufferGeometry();
hiEdgeGeom.setAttribute(
  "position",
  new THREE.BufferAttribute(hiEdgePos, 3).setUsage(THREE.DynamicDrawUsage),
);
hiEdgeGeom.setAttribute(
  "aColor",
  new THREE.BufferAttribute(hiEdgeCol, 3).setUsage(THREE.DynamicDrawUsage),
);
hiEdgeGeom.setAttribute(
  "aAlpha",
  new THREE.BufferAttribute(hiEdgeAlp, 1).setUsage(THREE.DynamicDrawUsage),
);

const hiEdgeMat = new THREE.ShaderMaterial({
  vertexShader: `
    attribute vec3 aColor; attribute float aAlpha;
    varying vec3 vColor; varying float vAlpha;
    void main() {
      vColor = aColor; vAlpha = aAlpha;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      gl_Position.z -= 0.05;
    }
  `,
  fragmentShader: `
    varying vec3 vColor; varying float vAlpha;
    void main() { gl_FragColor = vec4(vColor, vAlpha); }
  `,
  transparent: true,
  blending: THREE.AdditiveBlending,
  depthTest: false,
});
const hiLines = new THREE.LineSegments(hiEdgeGeom, hiEdgeMat);
scene.add(hiLines);

// --- TIMELINE ACTION ---
const slider = document.getElementById("timeline-slider");
const dateDisplay = document.getElementById("date-display");

function createLabel(id, parent, beforeEl) {
  const el = document.createElement("div");
  el.id = id;
  if (beforeEl) parent.insertBefore(el, beforeEl);
  else parent.appendChild(el);
  return el;
}

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

  const dateTop =
    document.getElementById("date-top") ||
    createLabel("date-top", dateDisplay.parentNode, slider);
  const countBottom =
    document.getElementById("count-bottom") ||
    createLabel("count-bottom", dateDisplay.parentNode, null);

  dateTop.textContent = dateStr;
  countBottom.textContent = activeSet.size;
  dateDisplay.style.display = "none"; // Hide original

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
    hiSiz[hiIdx] = p.size * 65; // Proportional to PageRank
    hiAlp[hiIdx] = 1.0;
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
    hiSiz[hiIdx] = p.size * 25; // Sub-highlights also proportional
    hiAlp[hiIdx] = 0.4;
    hiIdx++;
  });

  // Zero out rest to hide them
  for (let i = hiIdx; i < MAX_HI; i++) {
    hiSiz[i] = 0;
    hiAlp[i] = 0;
  }

  hiGeom.setDrawRange(0, hiIdx);
  hiGeom.attributes.position.needsUpdate = true;
  hiGeom.attributes.aColor.needsUpdate = true;
  hiGeom.attributes.aSize.needsUpdate = true;
  hiGeom.attributes.aAlpha.needsUpdate = true;

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
        a = 0.2;
      } else {
        // Neutral grey outgoing links
        r = 0.4;
        g = 0.4;
        b = 0.45;
        a = 0.2;
      }

      hiEdgeCol[o] = r;
      hiEdgeCol[o + 1] = g;
      hiEdgeCol[o + 2] = b;
      hiEdgeCol[o + 3] = r;
      hiEdgeCol[o + 4] = g;
      hiEdgeCol[o + 5] = b;
      hiEdgeAlp[hiEIdx * 2] = a;
      hiEdgeAlp[hiEIdx * 2 + 1] = a;
      hiEIdx++;
    });
  });
  hiEdgeGeom.setDrawRange(0, hiEIdx * 2);
  hiEdgeGeom.attributes.position.needsUpdate = true;
  hiEdgeGeom.attributes.aColor.needsUpdate = true;
  hiEdgeGeom.attributes.aAlpha.needsUpdate = true;
}

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
camera.position.set(0, 0, maxD * 0.42);

// --- LAYER 3: AMBIENT QUANTUM MIST ---
function createAmbientMist(THREE, scale) {
  const particleCount = 2000;
  const positions = new Float32Array(particleCount * 3);
  const sizes = new Float32Array(particleCount);
  for (let i = 0; i < particleCount; i++) {
    const angle = Math.random() * Math.PI * 2;
    const radius = scale * (Math.random() * 3.5);
    const height = (Math.random() - 0.5) * scale * 3;
    positions[i * 3] = Math.cos(angle) * radius;
    positions[i * 3 + 1] = height;
    positions[i * 3 + 2] = Math.sin(angle) * radius;
    sizes[i] = 1.0 + Math.random() * 3.0;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));

  const mat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: `
      precision highp float;
      uniform float uTime;
      attribute float aSize;
      varying float vAlpha;
      void main() {
        vec3 pos = position;
        // 3x Faster Drifting Logic
        pos.y += sin(uTime * 1.2 + position.x * 0.02) * 150.0;
        pos.x += cos(uTime * 0.9 + position.z * 0.02) * 90.0;
        
        vAlpha = 0.3 + 0.3 * abs(sin(uTime * 1.5 + position.x * 0.1));
        vec4 mvPos = modelViewMatrix * vec4(pos, 1.0);
        gl_Position = projectionMatrix * mvPos;
        gl_PointSize = aSize * (6000.0 / -mvPos.z);
      }
    `,
    fragmentShader: `
      precision highp float;
      varying float vAlpha;
      void main() {
        float d = length(gl_PointCoord - 0.5);
        if (d > 0.5) discard;
        // Radial beam/mist effect
        float glow = pow(max(0.0, 1.0 - d * 2.0), 3.0);
        gl_FragColor = vec4(vec3(1.0), glow * vAlpha);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  return new THREE.Points(geo, mat);
}

const ambientMist = createAmbientMist(THREE, maxD);
scene.add(ambientMist);

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
  const time = Date.now() * 0.001;
  hiMat.uniforms.uTime.value = time;
  ambientMist.material.uniforms.uTime.value = time;
  ambientMist.rotation.y += 0.01;

  // Ambient Breathing (Sub-Perceptual Parallax) - Moved to SCENE to avoid Camera conflict
  if (isRotating) {
    scene.position.x = Math.sin(time * 0.4) * 15;
    scene.position.y = Math.cos(time * 0.3) * 12;
  } else {
    scene.position.set(0, 0, 0);
  }

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
