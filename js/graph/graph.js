import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const loading = document.getElementById("loading");

// Load data
let data;
try {
  const response = await fetch("/graph/graph_data.json");
  if (!response.ok)
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  data = await response.json();
} catch (e) {
  loading.textContent = "";
  const errorDiv = document.createElement("div");
  errorDiv.style.color = "#f5576c";
  errorDiv.style.fontSize = "16px";
  errorDiv.textContent = "Failed to load graph data";
  const errorBr = document.createElement("br");
  const errorSmall = document.createElement("small");
  errorSmall.style.color = "#888";
  errorSmall.textContent = e.message;
  errorDiv.appendChild(errorBr);
  errorDiv.appendChild(errorSmall);
  loading.appendChild(errorDiv);
  throw e;
}

// Scene with subtle fog
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);
scene.fog = new THREE.FogExp2(0x000000, 0.0004);

// Camera
const camera = new THREE.PerspectiveCamera(
  75,
  window.innerWidth / window.innerHeight,
  0.1,
  5000,
);
camera.position.set(0, 0, 1000);

// Renderer
const renderer = new THREE.WebGLRenderer({
  antialias: true,
  powerPreference: "high-performance",
});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

// Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.minDistance = 100;
controls.maxDistance = 2000;

// Deck colors and cluster positions
const deckColors = {};
const deckAngles = {};
const colorPalette = [
  "#667eea",
  "#764ba2",
  "#f093fb",
  "#f5576c",
  "#4facfe",
  "#00f2fe",
  "#43e97b",
  "#38f9d7",
  "#fa709a",
  "#fee140",
  "#30cfd0",
  "#330867",
];

const uniqueDecks = [...new Set(data.nodes.map((n) => n.deck))];
uniqueDecks.forEach((deck, i) => {
  deckAngles[deck] = (i / uniqueDecks.length) * Math.PI * 2;
  deckColors[deck] = colorPalette[i % colorPalette.length];
});

const clusterRadius = 400;
const clusterSpread = 250;

// --- NODES (Points + ShaderMaterial) ---
const nodeCount = data.nodes.length;
const positions = new Float32Array(nodeCount * 3);
const colors = new Float32Array(nodeCount * 3);
const sizes = new Float32Array(nodeCount);

const nodeMap = new Map();
const nodeDeckMap = new Map();
const color = new THREE.Color();

data.nodes.forEach((node, i) => {
  const deckAngle = deckAngles[node.deck] || 0;

  const px =
    node.x ||
    Math.cos(deckAngle) * clusterRadius + (Math.random() - 0.5) * clusterSpread;
  const py =
    node.y ||
    Math.sin(deckAngle) * clusterRadius + (Math.random() - 0.5) * clusterSpread;
  const pz = node.z || (Math.random() - 0.5) * 150;

  positions[i * 3] = px;
  positions[i * 3 + 1] = py;
  positions[i * 3 + 2] = pz;

  nodeMap.set(node.id, { x: px, y: py, z: pz });
  nodeDeckMap.set(node.id, node.deck);

  const baseScale = 0.3 + node.pagerank * 200;
  sizes[i] = Math.max(3, Math.min(30, baseScale * 10));

  color.set(deckColors[node.deck] || "#ffffff");
  colors[i * 3] = color.r;
  colors[i * 3 + 1] = color.g;
  colors[i * 3 + 2] = color.b;
});

const nodeGeometry = new THREE.BufferGeometry();
nodeGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
nodeGeometry.setAttribute("aColor", new THREE.BufferAttribute(colors, 3));
nodeGeometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));

const nodeMaterial = new THREE.ShaderMaterial({
  uniforms: {
    uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
    fogColor: { value: scene.fog.color },
    fogDensity: { value: scene.fog.density },
  },
  vertexShader: `
    attribute float aSize;
    attribute vec3 aColor;
    varying vec3 vColor;
    varying float vFogFactor;
    void main() {
      vColor = aColor;
      vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
      gl_PointSize = aSize * uPixelRatio * (300.0 / -mvPos.z);
      gl_PointSize = clamp(gl_PointSize, 1.0, 64.0);
      gl_Position = projectionMatrix * mvPos;
      float fogDist = length(mvPos.xyz);
      vFogFactor = 1.0 - exp(-fogDensity * fogDensity * fogDist * fogDist);
    }
  `,
  fragmentShader: `
    uniform vec3 fogColor;
    varying vec3 vColor;
    varying float vFogFactor;
    void main() {
      // Hard circular cutoff — no soft edge, no rectangles
      float dist = length(gl_PointCoord - 0.5);
      if (dist > 0.45) discard;
      // Fake lighting: brighter toward top-left
      vec2 center = gl_PointCoord - 0.5;
      float light = 0.6 + 0.4 * dot(normalize(vec3(-center, 0.5)), vec3(-0.3, 0.3, 1.0));
      vec3 lit = vColor * light;
      vec3 finalColor = mix(lit, fogColor, vFogFactor);
      gl_FragColor = vec4(finalColor, 1.0);
    }
  `,
  depthWrite: false,
  depthTest: false,
});

const nodePoints = new THREE.Points(nodeGeometry, nodeMaterial);
scene.add(nodePoints);

// --- EDGES (LineSegments) ---
const deckColorCache = new Map();
for (const [deck, hex] of Object.entries(deckColors)) {
  deckColorCache.set(deck, new THREE.Color(hex));
}
const fallbackColor = new THREE.Color("#4facfe");

const edgePositions = [];
const edgeColors = [];

data.links.forEach((link) => {
  const sourcePos = nodeMap.get(link.source);
  const targetPos = nodeMap.get(link.target);
  if (sourcePos && targetPos) {
    edgePositions.push(
      sourcePos.x, sourcePos.y, sourcePos.z,
      targetPos.x, targetPos.y, targetPos.z,
    );
    const c = deckColorCache.get(nodeDeckMap.get(link.source)) || fallbackColor;
    const dim = 0.35;
    edgeColors.push(c.r * dim, c.g * dim, c.b * dim, c.r * dim, c.g * dim, c.b * dim);
  }
});

const edgeGeometry = new THREE.BufferGeometry();
edgeGeometry.setAttribute(
  "position",
  new THREE.Float32BufferAttribute(edgePositions, 3),
);
edgeGeometry.setAttribute(
  "color",
  new THREE.Float32BufferAttribute(edgeColors, 3),
);

const edgeMaterial = new THREE.LineBasicMaterial({
  vertexColors: true,
  depthWrite: false,
  depthTest: false,
});

const edgeLines = new THREE.LineSegments(edgeGeometry, edgeMaterial);
edgeLines.renderOrder = 0;
nodePoints.renderOrder = 1;
scene.add(edgeLines);

loading.style.display = "none";

// Animation
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

// Resize handler
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  nodeMaterial.uniforms.uPixelRatio.value = Math.min(window.devicePixelRatio, 2);
});
