#!/usr/bin/env python3
"""Quick 3D viz with 100 cards for testing"""

import sys, json, gzip, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')
from graph.builder import build_graph

def strip_html(text):
    """Remove HTML tags from text."""
    if not text:
        return ''
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove common Anki field separators
    text = text.replace('::', ' ').replace('\n', ' ')
    # Clean up whitespace
    text = ' '.join(text.split())[:60]
    return text


def scale_node_size(pagerank):
    """Scale node size based on PageRank."""
    return min(3, max(0.5, pagerank * 100))

# Load and take only 100
notes_file = "./data/cloudflare/collection/notes.json.gz"
with gzip.open(notes_file, 'rt') as f:
    all_notes = json.load(f)

sample_notes = all_notes[:100]
print(f"Using {len(sample_notes)} notes for quick test...")

graph = build_graph(sample_notes, with_pagerank=True)
print(f"Graph: {len(graph.nodes())} nodes, {len(graph.edges())} edges")

nodes = []
for node_id, data in graph.nodes(data=True):
    front = strip_html(data.get('front', 'Unknown'))
    pagerank = data.get('pagerank', 0)
    nodes.append({
        'id': node_id, 'label': front,
        'pagerank': round(pagerank, 6),
        'size': min(3, max(0.5, pagerank * 100)),
        'color': '#00ff88' if pagerank > 0.01 else '#00a8ff' if pagerank > 0.001 else '#888888'
    })

links = [{'source': s, 'target': t, 'weight': round(d.get('weight', 1), 2)} 
         for s, t, d in graph.edges(data=True)]

nodes.sort(key=lambda x: x['pagerank'], reverse=True)

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Anki 3D Graph - 100 Cards Test</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{overflow:hidden;background:#000;font-family:sans-serif}}
#canvas{{width:100vw;height:100vh}}
#info{{position:absolute;bottom:30px;left:30px;background:rgba(0,0,0,0.9);padding:25px;border-radius:16px;max-width:450px;border:1px solid rgba(0,255,136,0.3);display:none;z-index:100}}
#close{{position:absolute;top:15px;right:20px;cursor:pointer;font-size:28px;color:#666}}
#close:hover{{color:#00ff88}}
#loading{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:#00ff88;font-size:24px}}
</style>
</head>
<body>
<canvas id="canvas"></canvas>
<div id="loading">🚀 Launching...</div>
<div id="info">
<span id="close">&times;</span>
<h3 id="d-title" style="color:#00ff88;margin-bottom:15px"></h3>
<div class="stat"><span class="label">PageRank</span><span class="value" id="d-pr" style="color:#00ff88"></span></div>
<div class="stat"><span class="label">Size</span><span class="value" id="d-size" style="color:#00a8ff"></span></div>
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
const scene=new THREE.Scene();
scene.fog=new THREE.FogExp2(0x000000,0.0015);
const camera=new THREE.PerspectiveCamera(75,window.innerWidth/window.innerHeight,0.1,1000);
camera.position.z=300;
const renderer=new THREE.WebGLRenderer({{canvas:document.getElementById('canvas'),antialias:true}});
renderer.setSize(window.innerWidth,window.innerHeight);
const controls=new THREE.OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;
controls.autoRotate=false;  // Disabled - only rotate when dragging
controls.autoRotateSpeed=1;

const graphData={{nodes:{json.dumps(nodes)},links:{json.dumps(links)}}};
const nodeGeo=new THREE.SphereGeometry(1,32,32);
const meshes=[];

graphData.nodes.forEach(n=>{{
  const color=new THREE.Color(n.color);
  const mat=new THREE.MeshStandardMaterial({{color,color,emissive:color,emissiveIntensity:0.8,roughness:0.3,metalness:0.9}});
  const mesh=new THREE.Mesh(nodeGeo,mat);
  mesh.userData=n;
  meshes.push(mesh);
  scene.add(mesh);
}});

const positions=[];
const velocities=[];
for(let i=0;i<graphData.nodes.length;i++){{
  // Start in a tight sphere
  const theta=Math.random()*Math.PI*2;
  const phi=Math.acos(2*Math.random()-1);
  const r=50+Math.random()*50;
  positions.push({{
    x:r*Math.sin(phi)*Math.cos(theta),
    y:r*Math.sin(phi)*Math.sin(theta),
    z:r*Math.cos(phi)
  }});
  velocities.push({{x:0,y:0,z:0}});
}}

// Force-directed layout with bounds
for(let iter=0;iter<150;iter++){{
  for(let i=0;i<positions.length;i++){{
    for(let j=i+1;j<positions.length;j++){{
      const dx=positions[i].x-positions[j].x,dy=positions[i].y-positions[j].y,dz=positions[i].z-positions[j].z;
      const dist=Math.sqrt(dx*dx+dy*dy+dz*dz)||1;
      const force=20/(dist*dist);  // Reduced repulsion
      velocities[i].x+=(dx/dist)*force;velocities[i].y+=(dy/dist)*force;velocities[i].z+=(dz/dist)*force;
      velocities[j].x-=(dx/dist)*force;velocities[j].y-=(dy/dist)*force;velocities[j].z-=(dz/dist)*force;
    }}
    // Center gravity - keep nodes from flying away
    const distFromCenter=Math.sqrt(positions[i].x**2+positions[i].y**2+positions[i].z**2);
    if(distFromCenter>200){{
      velocities[i].x-=positions[i].x*0.01;
      velocities[i].y-=positions[i].y*0.01;
      velocities[i].z-=positions[i].z*0.01;
    }}
  }}
  graphData.links.forEach(link=>{{
    const si=graphData.nodes.findIndex(n=>n.id===link.source);
    const ti=graphData.nodes.findIndex(n=>n.id===link.target);
    if(si>=0&&ti>=0){{
      const dx=positions[si].x-positions[ti].x,dy=positions[si].y-positions[ti].y,dz=positions[si].z-positions[ti].z;
      velocities[si].x-=dx*0.003;velocities[si].y-=dy*0.003;velocities[si].z-=dz*0.003;
      velocities[ti].x+=dx*0.003;velocities[ti].y+=dy*0.003;velocities[ti].z+=dz*0.003;
    }}
  }});
  for(let i=0;i<positions.length;i++){{
    velocities[i].x*=0.85;velocities[i].y*=0.85;velocities[i].z*=0.85;  // Stronger damping
    positions[i].x+=velocities[i].x;positions[i].y+=velocities[i].y;positions[i].z+=velocities[i].z;
    // Hard bounds
    const maxPos=250;
    positions[i].x=Math.max(-maxPos,Math.min(maxPos,positions[i].x));
    positions[i].y=Math.max(-maxPos,Math.min(maxPos,positions[i].y));
    positions[i].z=Math.max(-maxPos,Math.min(maxPos,positions[i].z));
  }}
}}

positions.forEach((pos,i)=>{{
  meshes[i].position.set(pos.x,pos.y,pos.z);
  meshes[i].scale.setScalar(graphData.nodes[i].size*2);
}});

const edgeMat=new THREE.LineBasicMaterial({{color:0x00a8ff,transparent:true,opacity:0.4}});
const edgeGeo=new THREE.BufferGeometry();
const edgePos=[];
graphData.links.forEach(link=>{{
  const si=graphData.nodes.findIndex(n=>n.id===link.source);
  const ti=graphData.nodes.findIndex(n=>n.id===link.target);
  if(si>=0&&ti>=0){{
    edgePos.push(meshes[si].position.x,meshes[si].position.y,meshes[si].position.z);
    edgePos.push(meshes[ti].position.x,meshes[ti].position.y,meshes[ti].position.z);
  }}
}});
edgeGeo.setAttribute('position',new THREE.Float32BufferAttribute(edgePos,3));
const edges=new THREE.LineSegments(edgeGeo,edgeMat);
scene.add(edges);

const partGeo=new THREE.BufferGeometry();
const partCount=2000;
const partPos=[];
for(let i=0;i<partCount;i++){{
  partPos.push((Math.random()-0.5)*1000,(Math.random()-0.5)*1000,(Math.random()-0.5)*1000);
}}
partGeo.setAttribute('position',new THREE.Float32BufferAttribute(partPos,3));
const partMat=new THREE.PointsMaterial({{color:0x666666,size:1.5,transparent:true,opacity:0.6}});
const particles=new THREE.Points(partGeo,partMat);
scene.add(particles);

const composer=new THREE.EffectComposer(renderer);
composer.addPass(new THREE.RenderPass(scene,camera));
const bloom=new THREE.UnrealBloomPass(new THREE.Vector2(window.innerWidth,window.innerHeight),2,0.3,0.9);
composer.addPass(bloom);

document.getElementById('loading').style.display='none';

const raycaster=new THREE.Raycaster();
const mouse=new THREE.Vector2();
window.addEventListener('click',e=>{{
  mouse.x=(e.clientX/window.innerWidth)*2-1;
  mouse.y=-(e.clientY/window.innerHeight)*2+1;
  raycaster.setFromCamera(mouse,camera);
  const hits=raycaster.intersectObjects(meshes);
  if(hits.length>0){{
    const d=hits[0].object.userData;
    document.getElementById('info').style.display='block';
    document.getElementById('d-title').textContent=d.label;
    document.getElementById('d-pr').textContent=(d.pagerank*1000).toFixed(3);
    document.getElementById('d-size').textContent=(d.size*2).toFixed(2);
  }}
}});
document.getElementById('close').onclick=()=>document.getElementById('info').style.display='none';

function animate(){{
  requestAnimationFrame(animate);
  controls.update();
  meshes.forEach(m=>m.rotation.y+=0.02);
  composer.render();
}}
animate();

window.addEventListener('resize',()=>{{
  camera.aspect=window.innerWidth/window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth,window.innerHeight);
  composer.setSize(window.innerWidth,window.innerHeight);
}});
</script>
</body>
</html>'''

output_file = Path("./graph/index.html")
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ FAST! Created 3D viz with 100 cards")
print(f"🌐 Open: open {output_file}")
