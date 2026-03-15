#!/usr/bin/env python3
"""Create stunning 3D Three.js visualization of Anki knowledge graph"""

import sys, os, json, gzip
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21')
from graph.builder import build_graph

# Load staged notes
notes_file = "/Users/lz/Library/Application Support/Anki2/addons21/data/cloudflare/collection/notes.json.gz"
print("📦 Loading notes...")
with gzip.open(notes_file, 'rt') as f:
    all_notes = json.load(f)

# Take sample for performance
sample_notes = all_notes[:5000]
print(f"✓ Using {len(sample_notes):,} notes")

# Build graph
print("🔨 Building graph...")
graph = build_graph(sample_notes, with_pagerank=True)
print(f"✓ Graph: {len(graph.nodes()):,} nodes, {len(graph.edges()):,} edges")

# Prepare data
nodes = []
for node_id, data in graph.nodes(data=True):
    front = data.get('front', 'Unknown')[:60]
    pagerank = data.get('pagerank', 0)
    nodes.append({
        'id': node_id,
        'label': front,
        'pagerank': round(pagerank, 6),
        'size': min(3, max(0.5, pagerank * 100)),
        'color': '#00ff88' if pagerank > 0.01 else '#00a8ff' if pagerank > 0.001 else '#888888'
    })

links = []
for source, target, data in graph.edges(data=True):
    links.append({
        'source': source,
        'target': target,
        'weight': round(data.get('weight', 1), 2)
    })

# Sort by PageRank
nodes.sort(key=lambda x: x['pagerank'], reverse=True)
top_nodes = nodes[:50]

print("🎨 Creating 3D visualization...")

# Create HTML with Three.js
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Anki Knowledge Graph - 3D Visualization</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{overflow:hidden;background:#000;font-family:'Segoe UI',Roboto,sans-serif}}
#canvas{{width:100vw;height:100vh;position:fixed;top:0;left:0}}
#ui{{position:absolute;top:20px;left:20px;color:#fff;z-index:100;pointer-events:none}}
#panel{{background:rgba(0,0,0,0.7);backdrop-filter:blur(10px);padding:25px;border-radius:16px;max-width:380px;border:1px solid rgba(255,255,255,0.1);box-shadow:0 8px 32px rgba(0,255,136,0.1)}}
h1{{font-size:22px;margin-bottom:15px;background:linear-gradient(135deg,#00ff88,#00a8ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:700}}
.stat{{margin:10px 0;font-size:14px;display:flex;justify-content:space-between}}
.label{{color:#888}}
.value{{color:#fff;font-weight:600}}
#top50{{position:absolute;top:20px;right:20px;background:rgba(0,0,0,0.7);backdrop-filter:blur(10px);padding:20px;border-radius:16px;max-width:320px;max-height:70vh;overflow-y:auto;border:1px solid rgba(0,168,255,0.3);z-index:100}}
#top50 h2{{font-size:16px;margin-bottom:15px;color:#00a8ff}}
.rank{{padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.1);font-size:13px;transition:all 0.3s}}
.rank:hover{{background:rgba(0,255,136,0.1);padding-left:10px}}
.rn{{color:#00a8ff;width:35px;display:inline-block;font-weight:700}}
.rl{{color:#fff}}
.rp{{color:#00ff88;float:right;font-family:monospace}}
#info{{position:absolute;bottom:30px;left:30px;background:rgba(0,0,0,0.8);backdrop-filter:blur(10px);padding:25px;border-radius:16px;max-width:500px;border:1px solid rgba(0,255,136,0.3);display:none;z-index:100;box-shadow:0 8px 32px rgba(0,255,136,0.2)}}
#close{{position:absolute;top:15px;right:20px;cursor:pointer;font-size:28px;color:#666;transition:color 0.3s}}
#close:hover{{color:#00ff88}}
#controls{{position:absolute;bottom:30px;right:30px;background:rgba(0,0,0,0.7);backdrop-filter:blur(10px);padding:20px;border-radius:16px;border:1px solid rgba(255,255,255,0.1);z-index:100}}
.btn{{background:linear-gradient(135deg,#00ff88,#00a8ff);border:none;padding:12px 24px;color:#000;border-radius:8px;cursor:pointer;font-weight:600;margin:5px;transition:all 0.3s}}
.btn:hover{{transform:scale(1.05);box-shadow:0 0 20px rgba(0,255,136,0.5)}}
#loading{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:#00ff88;font-size:32px;z-index:1000;text-align:center}}
#loading p{{margin-top:15px;font-size:14px;color:#666}}
.legend{{margin-top:20px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.1)}}
.legend-item{{display:flex;align-items:center;margin:8px 0;font-size:13px}}
.dot{{width:14px;height:14px;border-radius:50%;margin-right:10px;box-shadow:0 0 10px currentColor}}
#stats{{position:absolute;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.7);backdrop-filter:blur(10px);padding:15px 30px;border-radius:30px;border:1px solid rgba(0,255,136,0.3);z-index:100;display:flex;gap:30px}}
#stats .stat{{margin:0;text-align:center}}
</style>
</head>
<body>
<canvas id="canvas"></canvas>

<div id="loading">
<div>🌌 Generating Universe...</div>
<p>This may take 30-60 seconds</p>
</div>

<div id="ui">
<div id="panel">
<h1>🌌 Anki Knowledge Universe</h1>
<div class="stat"><span class="label">Nodes</span><span class="value">{len(nodes):,}</span></div>
<div class="stat"><span class="label">Connections</span><span class="value">{len(links):,}</span></div>
<div class="stat"><span class="label">Sample</span><span class="value">5,000 notes</span></div>
<div class="stat"><span class="label">Generated</span><span class="value">{datetime.now().strftime('%Y-%m-%d')}</span></div>

<div class="legend">
<div class="legend-item"><div class="dot" style="background:#00ff88;box-shadow:0 0 15px #00ff88"></div><span>Hub Cards (Knowledge Centers)</span></div>
<div class="legend-item"><div class="dot" style="background:#00a8ff;box-shadow:0 0 10px #00a8ff"></div><span>Connected Concepts</span></div>
<div class="legend-item"><div class="dot" style="background:#888888"></div><span>Peripheral Knowledge</span></div>
</div>

<p style="margin-top:20px;font-size:12px;color:#666;line-height:1.6">
🖱️ Drag to rotate<br>
🔍 Scroll to zoom<br>
👆 Click nodes for details<br>
🎮 Right-click drag to pan
</p>
</div>
</div>

<div id="stats">
<div class="stat"><span class="label" style="color:#888">FPS</span><br><b id="fps" style="color:#00ff88;font-size:18px">60</b></div>
<div class="stat"><span class="label" style="color:#888">Nodes</span><br><b style="color:#00a8ff;font-size:18px">{len(nodes):,}</b></div>
<div class="stat"><span class="label" style="color:#888">Edges</span><br><b style="color:#00ff88;font-size:18px">{len(links):,}</b></div>
</div>

<div id="top50">
<h2>🏆 Top 50 Knowledge Hubs</h2>
{''.join(f'<div class="rank"><span class="rn">#{i+1}</span><span class="rl">{n["label"][:30]}</span><span class="rp">{n["pagerank"]*1000:.3f}</span></div>' for i,n in enumerate(top_nodes))}
</div>

<div id="info">
<span id="close">&times;</span>
<h3 id="d-title" style="color:#00ff88;margin-bottom:15px;font-size:20px"></h3>
<div class="stat"><span class="label">PageRank Score</span><span class="value" id="d-pr" style="color:#00ff88"></span></div>
<div class="stat"><span class="label">Node Size</span><span class="value" id="d-size" style="color:#00a8ff"></span></div>
<div class="stat"><span class="label">Node ID</span><span class="value" id="d-id" style="font-family:monospace;font-size:11px;color:#888"></span></div>
</div>

<div id="controls">
<button class="btn" onclick="resetCamera()">🎯 Reset View</button>
<button class="btn" onclick="toggleAutoRotate()">🔄 Auto Rotate</button>
<button class="btn" onclick="focusOnHub()">⭐ Focus Hub</button>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/EffectComposer.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/RenderPass.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/ShaderPass.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/shaders/CopyShader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/shaders/LuminosityHighPassShader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/UnrealBloomPass.js"></script>

<script>
// Scene setup
const scene=new THREE.Scene();
scene.fog=new THREE.FogExp2(0x000000,0.002);

const camera=new THREE.PerspectiveCamera(75,window.innerWidth/window.innerHeight,0.1,2000);
camera.position.z=500;

const renderer=new THREE.WebGLRenderer({canvas:document.getElementById('canvas'),antialias:true});
renderer.setSize(window.innerWidth,window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);

// Controls
const controls=new THREE.OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;
controls.dampingFactor=0.05;
controls.autoRotate=true;
controls.autoRotateSpeed=0.5;

// Graph data
const graphData={{nodes:{json.dumps(nodes)},links:{json.dumps(links)}}};

// Create nodes with glow
const nodeGeometry=new THREE.SphereGeometry(1,32,32);
const nodeMaterials={{}};
const nodes_meshes=[];

graphData.nodes.forEach((n,i)=>{{
  const color=new THREE.Color(n.color);
  const material=new THREE.MeshStandardMaterial({{
    color:color,
    emissive:color,
    emissiveIntensity:0.5,
    roughness:0.3,
    metalness:0.8
  }});
  
  const mesh=new THREE.Mesh(nodeGeometry,material);
  mesh.userData=n;
  nodes_meshes.push(mesh);
  scene.add(mesh);
}});

// Create edges with glow
const edgeMaterial=new THREE.LineBasicMaterial({{color:0x00a8ff,transparent:true,opacity:0.3}});
const edges_geometry=new THREE.BufferGeometry();
const edgePositions=[];

graphData.links.forEach(link=>{{
  const sourceIndex=graphData.nodes.findIndex(n=>n.id===link.source);
  const targetIndex=graphData.nodes.findIndex(n=>n.id===link.target);
  if(sourceIndex>=0&&targetIndex>=0){{
    edgePositions.push(0,0,0,0,0,0); // Will be updated
  }}
}});

edges_geometry.setAttribute('position',new THREE.Float32BufferAttribute(edgePositions,3));
const edges=new THREE.LineSegments(edges_geometry,edgeMaterial);
scene.add(edges);

// Position nodes in 3D space using force-directed layout simulation
const positions=[];
const velocities=[];
const repulsion=50,attraction=0.01,damping=0.9;

for(let i=0;i<graphData.nodes.length;i++){{
  positions.push({{
    x:(Math.random()-0.5)*400,
    y:(Math.random()-0.5)*400,
    z:(Math.random()-0.5)*400
  }});
  velocities.push({{x:0,y:0,z:0}});
}}

// Simple force simulation
for(let iter=0;iter<200;iter++){{
  // Repulsion
  for(let i=0;i<positions.length;i++){{
    for(let j=i+1;j<positions.length;j++){{
      const dx=positions[i].x-positions[j].x;
      const dy=positions[i].y-positions[j].y;
      const dz=positions[i].z-positions[j].z;
      const dist=Math.sqrt(dx*dx+dy*dy+dz*dz)||1;
      const force=repulsion/(dist*dist);
      const fx=(dx/dist)*force,fy=(dy/dist)*force,fz=(dz/dist)*force;
      velocities[i].x+=fx;velocities[i].y+=fy;velocities[i].z+=fz;
      velocities[j].x-=fx;velocities[j].y-=fy;velocities[j].z-=fz;
    }}
  }}
  
  // Attraction along edges
  graphData.links.forEach(link=>{{
    const si=graphData.nodes.findIndex(n=>n.id===link.source);
    const ti=graphData.nodes.findIndex(n=>n.id===link.target);
    if(si>=0&&ti>=0){{
      const dx=positions[si].x-positions[ti].x;
      const dy=positions[si].y-positions[ti].y;
      const dz=positions[si].z-positions[ti].z;
      velocities[si].x-=dx*attraction;velocities[si].y-=dy*attraction;velocities[si].z-=dz*attraction;
      velocities[ti].x+=dx*attraction;velocities[ti].y+=dy*attraction;velocities[ti].z+=dz*attraction;
    }}
  }});
  
  // Update positions
  for(let i=0;i<positions.length;i++){{
    velocities[i].x*=damping;velocities[i].y*=damping;velocities[i].z*=damping;
    positions[i].x+=velocities[i].x;positions[i].y+=velocities[i].y;positions[i].z+=velocities[i].z;
  }}
}}

// Apply positions
positions.forEach((pos,i)=>{{
  nodes_meshes[i].position.set(pos.x,pos.y,pos.z);
  nodes_meshes[i].scale.setScalar(graphData.nodes[i].size);
}});

// Update edge positions
const edgePosAttr=edges_geometry.attributes.position;
let edgeIdx=0;
graphData.links.forEach(link=>{{
  const si=graphData.nodes.findIndex(n=>n.id===link.source);
  const ti=graphData.nodes.findIndex(n=>n.id===link.target);
  if(si>=0&&ti>=0){{
    edgePosAttr.setXYZ(edgeIdx++,nodes_meshes[si].position.x,nodes_meshes[si].position.y,nodes_meshes[si].position.z);
    edgePosAttr.setXYZ(edgeIdx++,nodes_meshes[ti].position.x,nodes_meshes[ti].position.y,nodes_meshes[ti].position.z);
  }}
}});
edgePosAttr.needsUpdate=true;

// Particle background
const particles_geometry=new THREE.BufferGeometry();
const particleCount=5000;
const pPositions=[];
for(let i=0;i<particleCount;i++){{
  pPositions.push((Math.random()-0.5)*2000,(Math.random()-0.5)*2000,(Math.random()-0.5)*2000);
}}
particles_geometry.setAttribute('position',new THREE.Float32BufferAttribute(pPositions,3));
const particles_material=new THREE.PointsMaterial({{color:0x444444,size:2,transparent:true,opacity:0.5}});
const particles=new THREE.Points(particles_geometry,particles_material);
scene.add(particles);

// Post-processing - Bloom effect
const composer=new THREE.EffectComposer(renderer);
composer.addPass(new THREE.RenderPass(scene,camera));

const bloomPass=new THREE.UnrealBloomPass(new THREE.Vector2(window.innerWidth,window.innerHeight),1.5,0.4,0.85);
bloomPass.threshold=0;
bloomPass.strength=1.2;
bloomPass.radius=0.5;
composer.addPass(bloomPass);

// Hide loading
document.getElementById('loading').style.display='none';

// Interaction
const raycaster=new THREE.Raycaster();
const mouse=new THREE.Vector2();

window.addEventListener('click',onMouseClick);

function onMouseClick(event){{
  mouse.x=(event.clientX/window.innerWidth)*2-1;
  mouse.y=-(event.clientY/window.innerHeight)*2+1;
  raycaster.setFromCamera(mouse,camera);
  const intersects=raycaster.intersectObjects(nodes_meshes);
  if(intersects.length>0){{
    const d=intersects[0].object.userData;
    document.getElementById('info').style.display='block';
    document.getElementById('d-title').textContent=d.label;
    document.getElementById('d-pr').textContent=(d.pagerank*1000).toFixed(4);
    document.getElementById('d-size').textContent=d.size.toFixed(2);
    document.getElementById('d-id').textContent=d.id;
  }}
}};

document.getElementById('close').onclick=()=>document.getElementById('info').style.display='none';

// Controls functions
window.resetCamera=()=>{{
  camera.position.z=500;
  camera.position.x=0;
  camera.position.y=0;
  controls.target.set(0,0,0);
}};

window.toggleAutoRotate=()=>{{
  controls.autoRotate=!controls.autoRotate;
}};

window.focusOnHub=()=>{{
  if(nodes_meshes.length>0){{
    const hub=nodes_meshes[0];
    controls.target.copy(hub.position);
  }}
}};

// Animation
let lastTime=performance.now();
let frameCount=0;

function animate(){{
  requestAnimationFrame(animate);
  
  controls.update();
  
  // Gentle rotation
  nodes_meshes.forEach((mesh,i)=>{{
    mesh.rotation.y+=0.01;
  }});
  
  // FPS counter
  frameCount++;
  const now=performance.now();
  if(now-lastTime>=1000){{
    document.getElementById('fps').textContent=frameCount;
    frameCount=0;
    lastTime=now;
  }}
  
  composer.render();
}}

animate();

// Resize handler
window.addEventListener('resize',()=>{{
  camera.aspect=window.innerWidth/window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth,window.innerHeight);
  composer.setSize(window.innerWidth,window.innerHeight);
}});
</script>
</body>
</html>'''

# Save
output_file = Path("/Users/lz/Library/Application Support/Anki2/addons21/graph/index.html")
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Created stunning 3D visualization!")
print(f"🌐 Open in browser:")
print(f"   open {output_file}")
