/**
 * 3D Graph Visualization using Three.js
 * Renders knowledge graph with deck-based colors
 * Optimized with LOD and frustum culling for 10K+ nodes
 */

import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  stripHtml,
  assignDeckColor,
  positionNodes,
  scaleNodeSize,
} from "./viz_utils.js";
import {
  filterNodesByLOD,
  getLODLevel,
  distanceToCamera,
  getGeometryForLOD,
} from "./lod_utils.js";

/**
 * Main graph visualization class
 */
export class GraphVisualization {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      nodeGeometry: "sphere", // 'sphere', 'box', 'icosahedron'
      particleCount: 2000,
      ...options,
    };

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.nodes = [];
    this.nodeMeshes = [];
    this.deckColors = {};
    this.allNodes = null;
    this.links = [];
    this.lastLODUpdate = 0;

    this.init();
  }

  /**
   * Initialize Three.js scene
   */
  init() {
    // Scene
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x000000, 0.0015);

    // Camera - positioned to see all nodes
    this.camera = new THREE.PerspectiveCamera(
      75,
      this.container.clientWidth / this.container.clientHeight,
      0.1,
      3000,
    );
    this.camera.position.set(0, 0, 800);
    this.camera.lookAt(0, 0, 0);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.container,
      antialias: true,
    });
    this.renderer.setSize(
      this.container.clientWidth,
      this.container.clientHeight,
    );
    this.renderer.setPixelRatio(window.devicePixelRatio);

    // LIGHTS - Required for MeshStandardMaterial!
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(1, 1, 1);
    this.scene.add(directionalLight);

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
    directionalLight2.position.set(-1, -1, -1);
    this.scene.add(directionalLight2);

    console.log("✅ Lights added to scene");

    // Controls
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.autoRotate = false; // Only rotate when dragging
    this.controls.dampingFactor = 0.05;

    // Event listeners
    window.addEventListener("resize", () => this.onResize());

    // Start animation loop
    this.animate();

    console.log("✅ Scene initialized");
  }

  /**
   * Load and visualize graph data
   * @param {Array} nodes - Node data with deck information
   * @param {Array} links - Link data
   */
  loadData(nodes, links) {
    // Store all nodes for LOD updates
    this.allNodes = nodes.map((node) => ({
      ...node,
      label: stripHtml(node.label || node.front || "Unknown"),
      deck: node.deck || "Unknown",
    }));

    // Extract unique decks and assign colors
    const decks = [...new Set(this.allNodes.map((n) => n.deck))];
    decks.forEach((deck) => {
      if (!this.deckColors[deck]) {
        this.deckColors[deck] = assignDeckColor(deck);
      }
    });

    // Position all nodes using force-directed layout
    const positionedNodes = positionNodes(this.allNodes);
    this.allNodes = positionedNodes;

    // Store links
    this.links = links;

    // Create ALL nodes initially (no LOD on first load)
    this.createLODMeshes("high", this.allNodes);

    // DEBUG: Log node positions
    console.log(`Created ${this.allNodes.length} nodes`);
    console.log(
      "Sample positions:",
      this.allNodes.slice(0, 3).map((n) => ({
        id: n.id,
        x: n.x.toFixed(1),
        y: n.y.toFixed(1),
        z: n.z.toFixed(1),
      })),
    );

    // Create edge lines (all at once, optimized)
    this.createEdges(links);

    // Add particle background
    this.createParticles();

    // LOD runs automatically via animation loop (every 500ms)
    // No need to call updateLOD() here
  }

  /**
   * Update LOD based on camera position
   */
  updateLOD() {
    if (!this.allNodes || !this.camera) return;

    // Filter nodes by frustum + LOD
    const filtered = filterNodesByLOD(this.allNodes, this.camera);

    console.log("LOD Update:", {
      total: this.allNodes.length,
      high: filtered.high.length,
      medium: filtered.medium.length,
      low: filtered.low.length,
      culled: filtered.culled,
      cameraZ: this.camera.position.z,
    });

    // Clear old meshes
    this.nodeMeshes.forEach((mesh) => {
      this.scene.remove(mesh);
      if (mesh.geometry) mesh.geometry.dispose();
      if (mesh.material) mesh.material.dispose();
    });
    this.nodeMeshes = [];

    console.log(
      "Cleared meshes, scene now has",
      this.scene.children.length,
      "children",
    );

    // Create LOD meshes
    this.createLODMeshes("high", filtered.high);
    this.createLODMeshes("medium", filtered.medium);
    this.createLODMeshes("low", filtered.low);

    // Update counter
    const total =
      filtered.high.length + filtered.medium.length + filtered.low.length;
    console.log(
      `LOD: ${total} visible / ${this.allNodes.length} total (culled: ${filtered.culled})`,
    );
  }

  /**
   * Create meshes for specific LOD level - SIMPLE INDIVIDUAL MESHES
   */
  createLODMeshes(lodLevel, nodes) {
    if (!nodes || nodes.length === 0) {
      console.log(`No nodes for LOD ${lodLevel}`);
      return;
    }

    console.log(`Creating ${lodLevel} LOD for ${nodes.length} nodes`);

    const config = getGeometryForLOD(lodLevel);

    // Group by deck
    const deckGroups = {};
    nodes.forEach((node, i) => {
      const color = this.deckColors[node.deck];
      if (!deckGroups[color]) deckGroups[color] = [];
      deckGroups[color].push(node);
    });

    console.log(`  Decks: ${Object.keys(deckGroups).length}`);

    // Create one sphere per node (simple, reliable)
    Object.keys(deckGroups).forEach((color, idx) => {
      const group = deckGroups[color];
      const material = new THREE.MeshBasicMaterial({
        color: new THREE.Color(color),
      });

      group.forEach((node) => {
        const radius = 50; // HUGE for testing
        const geometry = new THREE.SphereGeometry(radius, 16, 16);
        const mesh = new THREE.Mesh(geometry, material);

        mesh.position.set(node.x, node.y, node.z);
        mesh.userData = { lodLevel, node };

        this.scene.add(mesh);
        this.nodeMeshes.push(mesh);
      });

      console.log(`  Deck ${color}: ${group.length} spheres`);
    });

    console.log(`Total meshes: ${this.nodeMeshes.length}`);
    console.log(`Scene children: ${this.scene.children.length}`);

    // FORCE render
    this.renderer.render(this.scene, this.camera);
    console.log("Render forced");
  }

  /**
   * Create edge lines between nodes (optimized with single BufferGeometry)
   */
  createEdges(links) {
    // Collect all edge positions in single array
    const positions = [];
    const colors = [];

    links.forEach((link) => {
      const sourceIndex = this.nodes.findIndex((n) => n.id === link.source);
      const targetIndex = this.nodes.findIndex((n) => n.id === link.target);

      if (sourceIndex >= 0 && targetIndex >= 0) {
        const sourceNode = this.nodes[sourceIndex];
        const sourceColor = new THREE.Color(this.deckColors[sourceNode.deck]);

        // Add source position
        positions.push(sourceNode.x, sourceNode.y, sourceNode.z);
        colors.push(sourceColor.r, sourceColor.g, sourceColor.b);

        // Add target position
        positions.push(
          targetIndex >= 0 ? this.nodes[targetIndex].x : 0,
          targetIndex >= 0 ? this.nodes[targetIndex].y : 0,
          targetIndex >= 0 ? this.nodes[targetIndex].z : 0,
        );
        colors.push(sourceColor.r, sourceColor.g, sourceColor.b);
      }
    });

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3),
    );
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.4,
    });

    const edges = new THREE.LineSegments(geometry, material);
    this.scene.add(edges);
  }

  /**
   * Create particle background (optimized: 500 particles instead of 2000)
   */
  createParticles() {
    const geometry = new THREE.BufferGeometry();
    const positions = [];

    for (let i = 0; i < 500; i++) {
      // Reduced from 2000
      positions.push(
        (Math.random() - 0.5) * 1000,
        (Math.random() - 0.5) * 1000,
        (Math.random() - 0.5) * 1000,
      );
    }

    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3),
    );

    const material = new THREE.PointsMaterial({
      color: 0x666666,
      size: 1.5,
      transparent: true,
      opacity: 0.6,
    });

    const particles = new THREE.Points(geometry, material);
    this.scene.add(particles);
  }

  /**
   * Handle window resize
   */
  onResize() {
    this.camera.aspect =
      this.container.clientWidth / this.container.clientHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(
      this.container.clientWidth,
      this.container.clientHeight,
    );
  }

  /**
   * Animation loop
   */
  animate() {
    requestAnimationFrame(() => this.animate());

    // Gentle rotation of nodes (only high LOD)
    this.nodeMeshes.forEach((mesh) => {
      if (mesh.userData.lodLevel === "high") {
        mesh.rotation.y += 0.01;
      }
    });

    this.controls.update();
    this.renderer.render(this.scene, this.camera);

    // LOD DISABLED FOR DEBUGGING - meshes keep getting cleared!
    // Update LOD every 500ms (not every frame for performance)
    // const now = Date.now();
    // if (now - this.lastLODUpdate > 500) {
    //   this.updateLOD();
    //   this.lastLODUpdate = now;
    // }
  }

  /**
   * Set up click interaction
   * @param {Function} callback - Called with node data on click
   */
  onNodeClick(callback) {
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    this.container.addEventListener("click", (event) => {
      const rect = this.renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, this.camera);
      const intersects = raycaster.intersectObjects(this.nodeMeshes);

      if (intersects.length > 0) {
        callback(intersects[0].object.userData);
      }
    });
  }
}

/**
 * Initialize visualization from JSON data
 * @param {string} containerId - DOM element ID
 * @param {Object} data - { nodes, links }
 * @returns {GraphVisualization}
 */
export function initGraph(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) {
    throw new Error(`Container #${containerId} not found`);
  }

  const viz = new GraphVisualization(container);
  viz.loadData(data.nodes, data.links);

  return viz;
}
