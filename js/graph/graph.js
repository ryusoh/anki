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

// Camera
const camera = new THREE.PerspectiveCamera(
  75,
  window.innerWidth / window.innerHeight,
  0.1,
  50000,
);
camera.position.set(0, 0, 10000);

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
controls.maxDistance = 20000;

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

// Count nodes per deck for spread scaling
const deckCounts = {};
data.nodes.forEach((n) => {
  deckCounts[n.deck] = (deckCounts[n.deck] || 0) + 1;
});

// Spread scales with sqrt of deck size — 100 nodes → 250, 25000 nodes → ~4000
const deckSpread = {};
uniqueDecks.forEach((deck) => {
  deckSpread[deck] = Math.max(250, Math.sqrt(deckCounts[deck]) * 25);
});

// Cluster radius scales so larger spreads don't overlap
const maxSpread = Math.max(...Object.values(deckSpread));
const clusterRadius = maxSpread * 1.5 + 200;

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
  const spread = deckSpread[node.deck] || 250;

  const px =
    node.x ||
    Math.cos(deckAngle) * clusterRadius + (Math.random() - 0.5) * spread;
  const py =
    node.y ||
    Math.sin(deckAngle) * clusterRadius + (Math.random() - 0.5) * spread;
  const pz = node.z || (Math.random() - 0.5) * spread * 0.3;

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
  },
  vertexShader: `
    uniform float uPixelRatio;
    attribute float aSize;
    attribute vec3 aColor;
    varying vec3 vColor;
    void main() {
      vColor = aColor;
      vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
      gl_PointSize = aSize * uPixelRatio * (300.0 / -mvPos.z);
      gl_PointSize = clamp(gl_PointSize, 1.0, 64.0);
      gl_Position = projectionMatrix * mvPos;
    }
  `,
  fragmentShader: `
    varying vec3 vColor;
    void main() {
      float dist = length(gl_PointCoord - 0.5);
      if (dist > 0.45) discard;
      vec2 center = gl_PointCoord - 0.5;
      float light = 0.6 + 0.4 * dot(normalize(vec3(-center, 0.5)), vec3(-0.3, 0.3, 1.0));
      gl_FragColor = vec4(vColor * light, 1.0);
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

// Find weight range for normalization
let minWeight = Infinity;
let maxWeight = -Infinity;
data.links.forEach((link) => {
  const w = link.weight || 1;
  if (w < minWeight) minWeight = w;
  if (w > maxWeight) maxWeight = w;
});
const weightRange = maxWeight - minWeight || 1;

// Only keep strongest edges (weight >= max weight)
data.links.forEach((link) => {
  const sourcePos = nodeMap.get(link.source);
  const targetPos = nodeMap.get(link.target);
  if (sourcePos && targetPos && (link.weight || 1) >= maxWeight) {
    edgePositions.push(
      sourcePos.x,
      sourcePos.y,
      sourcePos.z,
      targetPos.x,
      targetPos.y,
      targetPos.z,
    );
    const c = deckColorCache.get(nodeDeckMap.get(link.source)) || fallbackColor;
    edgeColors.push(
      c.r * 0.5,
      c.g * 0.5,
      c.b * 0.5,
      c.r * 0.5,
      c.g * 0.5,
      c.b * 0.5,
    );
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
  nodeMaterial.uniforms.uPixelRatio.value = Math.min(
    window.devicePixelRatio,
    2,
  );
});
