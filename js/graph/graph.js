import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { escapeHtml } from "#js/transactions/utils.js";

const loading = document.getElementById("loading");

// Load data
let data;
try {
  const response = await fetch("/graph/graph_data.json");
  if (!response.ok)
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  data = await response.json();
} catch (e) {
  loading.innerHTML = `<div style="color:#f5576c;font-size:16px;">Failed to load graph data<br><small style="color:#888">${escapeHtml(e.message)}</small></div>`;
  throw e;
}

// Scene with subtle fog
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x050510);
scene.fog = new THREE.FogExp2(0x050510, 0.002);

// Camera
const camera = new THREE.PerspectiveCamera(
  75,
  window.innerWidth / window.innerHeight,
  0.1,
  5000,
);
camera.position.set(0, 0, 1000);

// Renderer with better quality
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

// Lights for depth
const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
scene.add(ambientLight);

const pointLight = new THREE.PointLight(0x667eea, 1, 1000);
pointLight.position.set(200, 200, 200);
scene.add(pointLight);

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
const nodeRadius = 8;

// --- NODES (INSTANCED MESH) ---
const nodeCount = data.nodes.length;
const geometry = new THREE.SphereGeometry(nodeRadius, 8, 8);
const material = new THREE.MeshPhongMaterial({
  shininess: 100,
  specular: 0x444444,
  vertexColors: false,
});

const instancedMesh = new THREE.InstancedMesh(geometry, material, nodeCount);
const dummy = new THREE.Object3D();
const color = new THREE.Color();

// Maps for O(1) lookup during edge creation
const nodeMap = new Map();
const nodeDeckMap = new Map();

data.nodes.forEach((node, i) => {
  const deckAngle = deckAngles[node.deck] || 0;

  const px =
    node.x ||
    Math.cos(deckAngle) * clusterRadius + (Math.random() - 0.5) * clusterSpread;
  const py =
    node.y ||
    Math.sin(deckAngle) * clusterRadius + (Math.random() - 0.5) * clusterSpread;
  const pz = node.z || (Math.random() - 0.5) * 150;

  nodeMap.set(node.id, { x: px, y: py, z: pz });
  nodeDeckMap.set(node.id, node.deck);

  dummy.position.set(px, py, pz);

  const baseScale = 0.3 + node.pagerank * 200;
  const finalScale = Math.max(0.3, Math.min(3, baseScale));
  dummy.scale.setScalar(finalScale);
  dummy.updateMatrix();

  instancedMesh.setMatrixAt(i, dummy.matrix);

  color.set(deckColors[node.deck] || "#ffffff");
  instancedMesh.setColorAt(i, color);
});

scene.add(instancedMesh);

// --- EDGES (INSTANCED CYLINDERS FOR VISIBLE THICKNESS) ---
const edgeRadius = 0.6;
const edgeCylinderGeo = new THREE.CylinderGeometry(
  edgeRadius,
  edgeRadius,
  1,
  4,
  1,
);
edgeCylinderGeo.translate(0, 0.5, 0);
edgeCylinderGeo.rotateX(Math.PI / 2);

const edgeMaterial = new THREE.MeshPhongMaterial({
  transparent: true,
  opacity: 0.35,
  shininess: 80,
  specular: 0x222222,
  blending: THREE.AdditiveBlending,
});

// Collect valid edges
const validEdges = [];
const deckColorCache = new Map();
for (const [deck, hex] of Object.entries(deckColors)) {
  deckColorCache.set(deck, new THREE.Color(hex));
}
const fallbackColor = new THREE.Color("#4facfe");

data.links.forEach((link) => {
  const sourcePos = nodeMap.get(link.source);
  const targetPos = nodeMap.get(link.target);
  if (sourcePos && targetPos) {
    validEdges.push({
      sourcePos,
      targetPos,
      deck: nodeDeckMap.get(link.source),
    });
  }
});

const edgeMesh = new THREE.InstancedMesh(
  edgeCylinderGeo,
  edgeMaterial,
  validEdges.length,
);
const edgeDummy = new THREE.Object3D();
const edgeColor = new THREE.Color();
const up = new THREE.Vector3(0, 0, 1);

validEdges.forEach((edge, i) => {
  const src = new THREE.Vector3(
    edge.sourcePos.x,
    edge.sourcePos.y,
    edge.sourcePos.z,
  );
  const tgt = new THREE.Vector3(
    edge.targetPos.x,
    edge.targetPos.y,
    edge.targetPos.z,
  );
  const dir = new THREE.Vector3().subVectors(tgt, src);
  const len = dir.length();

  edgeDummy.position.copy(src);
  edgeDummy.scale.set(1, 1, len);
  edgeDummy.quaternion.setFromUnitVectors(up, dir.normalize());
  edgeDummy.updateMatrix();

  edgeMesh.setMatrixAt(i, edgeDummy.matrix);

  edgeColor.copy(deckColorCache.get(edge.deck) || fallbackColor);
  edgeMesh.setColorAt(i, edgeColor);
});

edgeMesh.instanceMatrix.needsUpdate = true;
edgeMesh.instanceColor.needsUpdate = true;
scene.add(edgeMesh);

loading.style.display = "none";

// Animation
let time = 0;
function animate() {
  requestAnimationFrame(animate);
  time += 0.001;

  instancedMesh.rotation.y = Math.sin(time) * 0.05;
  edgeMesh.rotation.y = Math.sin(time) * 0.05;

  controls.update();
  renderer.render(scene, camera);
}
animate();

// Resize handler
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
