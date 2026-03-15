/**
 * Level of Detail (LOD) and Frustum Culling Utilities
 * Optimizes rendering for 10,000+ nodes
 */

import * as THREE from "three";

/**
 * Check if a node is visible in camera frustum
 * @param {Object} node - Node with x, y, z
 * @param {THREE.Frustum} frustum - Camera frustum
 * @returns {boolean}
 */
export function isVisibleInFrustum(node, frustum) {
  const point = new THREE.Vector3(node.x, node.y, node.z);
  return frustum.containsPoint(point);
}

/**
 * Cull nodes outside camera view
 * @param {Array} nodes - All nodes
 * @param {THREE.Frustum} frustum - Camera frustum
 * @returns {Array} Visible nodes
 */
export function cullNodes(nodes, frustum) {
  if (!nodes || nodes.length === 0) return [];

  return nodes.filter((node) => isVisibleInFrustum(node, frustum));
}

/**
 * Get LOD level based on distance from camera
 * @param {number} distance - Distance from camera
 * @returns {string} LOD level
 */
export function getLODLevel(distance) {
  if (distance < 200) return "high"; // Full detail (16 segments)
  if (distance < 500) return "medium"; // Medium detail (8 segments)
  if (distance < 1000) return "low"; // Low detail (4 segments)
  return "low"; // Always show something (was: hidden)
}

/**
 * Get geometry configuration for LOD level
 * @param {string} level - LOD level
 * @returns {Object} Geometry config
 */
export function getGeometryForLOD(level) {
  switch (level) {
    case "high":
      return { segments: 16, size: 1.0 };
    case "medium":
      return { segments: 8, size: 0.8 };
    case "low":
      return { segments: 4, size: 0.5 };
    default:
      return { segments: 4, size: 0.3 };
  }
}

/**
 * Calculate distance from camera to node
 * @param {Object} node - Node with x, y, z
 * @param {Object} cameraPos - Camera position
 * @returns {number} Distance
 */
export function distanceToCamera(node, cameraPos) {
  const dx = node.x - cameraPos.x;
  const dy = node.y - cameraPos.y;
  const dz = node.z - cameraPos.z;
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

/**
 * Get LOD statistics for monitoring
 * @param {Array} nodes - All nodes
 * @param {Object} cameraPos - Camera position
 * @returns {Object} LOD distribution
 */
export function getLODStats(nodes, cameraPos) {
  const stats = { high: 0, medium: 0, low: 0, hidden: 0 };

  nodes.forEach((node) => {
    const dist = distanceToCamera(node, cameraPos);
    const level = getLODLevel(dist);
    stats[level]++;
  });

  return stats;
}

/**
 * Group nodes by deck for instanced rendering
 * @param {Array} nodes - Nodes to group
 * @returns {Object} Groups by deck
 */
export function groupByDeck(nodes) {
  const groups = {};

  nodes.forEach((node) => {
    const deck = node.deck || "Unknown";
    if (!groups[deck]) groups[deck] = [];
    groups[deck].push(node);
  });

  return groups;
}

/**
 * Load nodes in batches for progressive rendering
 * @param {Array} nodes - All nodes
 * @param {number} batchSize - Nodes per batch
 * @returns {Array} Batches of nodes
 */
export function loadNodesInBatches(nodes, batchSize = 100) {
  const batches = [];

  for (let i = 0; i < nodes.length; i += batchSize) {
    batches.push(nodes.slice(i, i + batchSize));
  }

  return batches;
}

/**
 * Prioritize nodes for progressive loading
 * @param {Array} nodes - All nodes
 * @param {Object} cameraPos - Camera position
 * @param {number} limit - Max nodes to load initially
 * @returns {Array} Prioritized nodes
 */
export function prioritizeNodes(nodes, cameraPos, limit = 1000) {
  // Calculate priority score (distance + deck diversity)
  const scored = nodes.map((node) => ({
    ...node,
    score: 1 / (distanceToCamera(node, cameraPos) + 1),
  }));

  // Sort by score
  scored.sort((a, b) => b.score - a.score);

  // Return top N
  return scored.slice(0, limit);
}

/**
 * Create frustum from camera
 * @param {THREE.Camera} camera
 * @returns {THREE.Frustum}
 */
export function createFrustum(camera) {
  const frustum = new THREE.Frustum();
  const projMatrix = new THREE.Matrix4();
  projMatrix.multiplyMatrices(
    camera.projectionMatrix,
    camera.matrixWorldInverse,
  );
  frustum.setFromProjectionMatrix(projMatrix);
  return frustum;
}

/**
 * Optimized node filtering with frustum culling + LOD
 * @param {Array} nodes - All nodes
 * @param {THREE.Camera} camera
 * @returns {Object} Filtered nodes by LOD level
 */
export function filterNodesByLOD(nodes, camera) {
  const frustum = createFrustum(camera);
  const cameraPos = {
    x: camera.position.x,
    y: camera.position.y,
    z: camera.position.z,
  };

  const result = {
    high: [],
    medium: [],
    low: [],
    culled: 0,
  };

  // Debug: check first node
  if (nodes.length > 0) {
    const firstNode = nodes[0];
    const dist = distanceToCamera(firstNode, cameraPos);
    const level = getLODLevel(dist);
    console.log("First node debug:", {
      position: firstNode,
      cameraPos,
      distance: dist.toFixed(1),
      lodLevel: level,
    });
  }

  nodes.forEach((node) => {
    // Check LOD first (distance-based)
    const dist = distanceToCamera(node, cameraPos);
    const level = getLODLevel(dist);

    // Then check frustum (only cull if VERY far outside)
    const inFrustum = isVisibleInFrustum(node, frustum);

    if (!inFrustum && dist > cameraPos.z * 1.5) {
      // Only cull if outside frustum AND far away
      result.culled++;
      return;
    }

    // Assign to LOD level
    if (level === "high") {
      result.high.push(node);
    } else if (level === "medium") {
      result.medium.push(node);
    } else {
      result.low.push(node);
    }
  });

  return result;
}
