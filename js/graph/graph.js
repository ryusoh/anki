import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GRAPH_BACKGROUND_IMAGE } from "#js/config.js";

if (GRAPH_BACKGROUND_IMAGE.enabled) {
  document.body.style.setProperty(
    "background",
    "#000 url(../assets/backgrounds/graph_background.jpg) center center no-repeat",
    "important",
  );
  document.body.style.setProperty("background-size", "cover", "important");
}

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
scene.background = null;

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
  alpha: true,
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
const colorPalette = [
  "#00C7BE", // Teal
  "#32ADE6", // Cyan
  "#0A84FF", // Blue
  "#5E5CE6", // Indigo
  "#AF52DE", // Purple
  "#BF5AF2", // Light Purple
  "#FF2D55", // Pink
  "#FF375F", // Rose
  "#FF3B30", // Red
  "#FF9500", // Orange
  "#FFCC00", // Yellow
  "#8E8E93", // Gray
];

const uniqueDecks = [...new Set(data.nodes.map((n) => n.deck))];
// Fibonacci sphere for even 3D distribution of cluster centers
const deckCenters = {};
const goldenAngle = Math.PI * (3 - Math.sqrt(5));
uniqueDecks.forEach((deck, i) => {
  const y = 1 - (2 * i + 1) / uniqueDecks.length; // -1 to 1
  const radiusAtY = Math.sqrt(1 - y * y);
  const theta = goldenAngle * i;
  deckCenters[deck] = {
    x: Math.cos(theta) * radiusAtY,
    y: y,
    z: Math.sin(theta) * radiusAtY,
  };
  deckColors[deck] = colorPalette[i % colorPalette.length];
});

// Check if nodes have pre-computed positions
const hasLayout = data.nodes.length > 0 && data.nodes[0].x != null;

// Fallback cluster layout for nodes without pre-computed positions
const deckCounts = {};
data.nodes.forEach((n) => {
  deckCounts[n.deck] = (deckCounts[n.deck] || 0) + 1;
});
// Sphere radius per deck scales with cube root (volume-proportional)
const deckSpread = {};
uniqueDecks.forEach((deck) => {
  deckSpread[deck] = Math.max(100, Math.cbrt(deckCounts[deck]) * 30);
});
const maxSpread = Math.max(...Object.values(deckSpread));
const clusterRadius = maxSpread * 2;

// --- NODES (Points + ShaderMaterial) ---
const nodeCount = data.nodes.length;
const positions = new Float32Array(nodeCount * 3);
const colors = new Float32Array(nodeCount * 3);
const sizes = new Float32Array(nodeCount);

const nodeMap = new Map();
const nodeDeckMap = new Map();
const color = new THREE.Color();

data.nodes.forEach((node, i) => {
  const center = deckCenters[node.deck] || { x: 0, y: 0, z: 0 };
  const spread = deckSpread[node.deck] || 100;

  let px, py, pz;
  if (hasLayout) {
    px = node.x;
    py = node.y;
    pz = node.z !== undefined ? node.z : (Math.random() - 0.5) * spread * 0.5;
  } else {
    // Spherical distribution within cluster
    const r = spread * Math.cbrt(Math.random());
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    px = center.x * clusterRadius + r * Math.sin(phi) * Math.cos(theta);
    py = center.y * clusterRadius + r * Math.sin(phi) * Math.sin(theta);
    pz = center.z * clusterRadius + r * Math.cos(phi);
  }

  positions[i * 3] = px;
  positions[i * 3 + 1] = py;
  positions[i * 3 + 2] = pz;

  nodeMap.set(node.id, { x: px, y: py, z: pz });
  nodeDeckMap.set(node.id, node.deck);

  const sizeFactor = nodeCount > 50000 ? 0.5 : nodeCount > 10000 ? 0.75 : 1.0;
  const baseScale = 0.3 + node.pagerank * 200;
  sizes[i] = Math.max(
    3 * sizeFactor,
    Math.min(30 * sizeFactor, baseScale * 10 * sizeFactor),
  );

  color.set(deckColors[node.deck] || "#ffffff");
  colors[i * 3] = color.r;
  colors[i * 3 + 1] = color.g;
  colors[i * 3 + 2] = color.b;
});

const nodeGeometry = new THREE.BufferGeometry();
nodeGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
nodeGeometry.setAttribute("aColor", new THREE.BufferAttribute(colors, 3));
nodeGeometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));

const baseAlpha = nodeCount > 50000 ? 0.15 : nodeCount > 10000 ? 0.25 : 0.4;

const nodeMaterial = new THREE.ShaderMaterial({
  uniforms: {
    uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
    uBaseAlpha: { value: baseAlpha },
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
    uniform float uBaseAlpha;
    varying vec3 vColor;
    void main() {
      vec2 center = gl_PointCoord - 0.5;
      float dist = length(center);
      // Soft radial gradient
      float alpha = smoothstep(0.5, 0.0, dist);
      // Soft core
      float core = smoothstep(0.15, 0.0, dist);
      vec3 finalColor = mix(vColor, vec3(1.0), core * 0.2);
      
      float finalAlpha = alpha * uBaseAlpha;
      // Explicitly premultiply alpha for correct CSS background compositing
      gl_FragColor = vec4(finalColor * finalAlpha, finalAlpha);
    }
  `,
  transparent: true,
  depthWrite: false,
  depthTest: false,
});

const nodePoints = new THREE.Points(nodeGeometry, nodeMaterial);
scene.add(nodePoints);

// Auto-fit camera to data bounds
let maxDist = 0;
for (let i = 0; i < nodeCount; i++) {
  const dx = positions[i * 3];
  const dy = positions[i * 3 + 1];
  const dz = positions[i * 3 + 2];
  const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
  if (d > maxDist) maxDist = d;
}
maxDist = Math.max(maxDist, 100); // minimum bound
camera.position.set(0, 0, maxDist * 2.5);
camera.far = maxDist * 20;
camera.updateProjectionMatrix();
controls.minDistance = maxDist * 0.05;
controls.maxDistance = maxDist * 10;

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

const edgeOpacity = nodeCount > 50000 ? 0.015 : nodeCount > 10000 ? 0.05 : 0.15;

const edgeMaterial = new THREE.LineBasicMaterial({
  vertexColors: true,
  transparent: true,
  opacity: edgeOpacity,
  depthWrite: false,
  depthTest: false,
});

const edgeLines = new THREE.LineSegments(edgeGeometry, edgeMaterial);
edgeLines.renderOrder = 0;
nodePoints.renderOrder = 1;
scene.add(edgeLines);

loading.style.display = "none";

// Keyboard navigation
const keyState = {};
window.addEventListener("keydown", (e) => {
  keyState[e.key] = true;
});
window.addEventListener("keyup", (e) => {
  keyState[e.key] = false;
});

// Animation
function animate() {
  requestAnimationFrame(animate);
  handleKeys();
  controls.update();
  renderer.render(scene, camera);
}
animate();

function handleKeys() {
  const speed = 15;
  // Get camera's local axes
  const forward = new THREE.Vector3();
  camera.getWorldDirection(forward);
  const right = new THREE.Vector3()
    .crossVectors(forward, camera.up)
    .normalize();
  const up = camera.up.clone();

  if (keyState["ArrowUp"] || keyState["w"]) {
    controls.target.addScaledVector(up, speed);
    camera.position.addScaledVector(up, speed);
  }
  if (keyState["ArrowDown"] || keyState["s"]) {
    controls.target.addScaledVector(up, -speed);
    camera.position.addScaledVector(up, -speed);
  }
  if (keyState["ArrowRight"] || keyState["d"]) {
    controls.target.addScaledVector(right, speed);
    camera.position.addScaledVector(right, speed);
  }
  if (keyState["ArrowLeft"] || keyState["a"]) {
    controls.target.addScaledVector(right, -speed);
    camera.position.addScaledVector(right, -speed);
  }
}

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
