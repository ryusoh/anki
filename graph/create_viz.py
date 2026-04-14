#!/usr/bin/env python3
"""Create interactive HTML visualization of Anki knowledge graph"""

import sys, os, json, gzip
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')
from graph.builder import build_graph

# Load staged notes
notes_file = "./data/cloudflare/collection/notes.json.gz"
print("Loading notes...")
with gzip.open(notes_file, 'rt') as f:
    all_notes = json.load(f)

# Take sample for performance
sample_notes = all_notes[:5000]
print(f"✓ Using {len(sample_notes):,} notes")

# Build graph
print("Building graph...")
graph = build_graph(sample_notes, with_pagerank=True)
print(f"✓ Graph: {len(graph.nodes()):,} nodes, {len(graph.edges()):,} edges")

# Prepare data for D3
nodes = []
for node_id, data in graph.nodes(data=True):
    front = data.get('front', 'Unknown')[:50]
    pagerank = data.get('pagerank', 0)
    nodes.append({
        'id': node_id,
        'label': front,
        'pagerank': round(pagerank, 6),
        'size': min(25, max(5, int(pagerank * 5000))),
        'color': '#4CAF50' if pagerank > 0.01 else '#2196F3' if pagerank > 0.001 else '#9E9E9E'
    })

links = []
for source, target, data in graph.edges(data=True):
    links.append({
        'source': source,
        'target': target,
        'weight': round(data.get('weight', 1), 2)
    })

# Sort nodes by PageRank (top first)
nodes.sort(key=lambda x: x['pagerank'], reverse=True)
top_nodes = nodes[:100]  # Top 100 for display

# Create HTML
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Anki Knowledge Graph</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#fff;overflow:hidden}}
#viz{{width:100vw;height:100vh}}
#panel{{position:absolute;top:20px;left:20px;background:rgba(0,0,0,0.85);padding:20px;border-radius:12px;max-width:350px;border:1px solid #333;z-index:100}}
h1{{font-size:20px;margin-bottom:15px;color:#4CAF50}}
.stat{{margin:8px 0;font-size:14px}}
.label{{color:#888;margin-right:8px}}
#details{{position:absolute;bottom:20px;left:20px;background:rgba(0,0,0,0.95);padding:20px;border-radius:12px;max-width:450px;border:1px solid #4CAF50;display:none;z-index:100}}
#close{{position:absolute;top:10px;right:15px;cursor:pointer;font-size:24px;color:#888}}
#close:hover{{color:#fff}}
.node{{cursor:pointer;stroke:#fff;stroke-width:1.5}}
.link{{stroke:#444;stroke-opacity:0.4}}
#top100{{position:absolute;top:20px;right:20px;background:rgba(0,0,0,0.85);padding:15px;border-radius:12px;max-width:300px;max-height:80vh;overflow-y:auto;border:1px solid #333;z-index:100}}
#top100 h2{{font-size:16px;margin-bottom:10px;color:#2196F3}}
.rank{{padding:5px 0;border-bottom:1px solid #222;font-size:13px}}
.rank:hover{{background:#222}}
.rn{{color:#888;width:30px;display:inline-block}}
.rl{{color:#fff}}
.rp{{color:#4CAF50;float:right}}
#loading{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:28px;color:#4CAF50}}
.legend{{margin-top:15px;padding-top:15px;border-top:1px solid #333}}
.legend-item{{display:flex;align-items:center;margin:5px 0}}
.dot{{width:12px;height:12px;border-radius:50%;margin-right:8px}}
</style>
</head>
<body>
<div id="viz"></div>
<div id="loading">📊 Building graph...</div>

<div id="panel">
<h1>📊 Anki Knowledge Graph</h1>
<div class="stat"><span class="label">Total nodes:</span><b>{len(nodes):,}</b></div>
<div class="stat"><span class="label">Total edges:</span><b>{len(links):,}</b></div>
<div class="stat"><span class="label">Sample:</span>5,000 notes</div>
<div class="stat"><span class="label">Exported:</span>{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>

<div class="legend">
<div class="legend-item"><div class="dot" style="background:#4CAF50"></div><span>Hub cards (high PageRank)</span></div>
<div class="legend-item"><div class="dot" style="background:#2196F3"></div><span>Connected cards</span></div>
<div class="legend-item"><div class="dot" style="background:#9E9E9E"></div><span>Isolated cards</span></div>
</div>

<p style="margin-top:15px;font-size:12px;color:#666">
💡 Drag to move nodes<br>
🔍 Scroll to zoom<br>
👆 Click node for details
</p>
</div>

<div id="top100">
<h2>🏆 Top 100 by PageRank</h2>
{''.join(f'<div class="rank"><span class="rn">#{i+1}</span><span class="rl">{n["label"][:35]}</span><span class="rp">{n["pagerank"]*1000:.2f}</span></div>' for i,n in enumerate(top_nodes))}
</div>

<div id="details">
<span id="close">&times;</span>
<h3 id="d-title" style="color:#4CAF50;margin-bottom:15px;font-size:18px"></h3>
<div class="stat"><span class="label">PageRank:</span><b id="d-pr"></b></div>
<div class="stat"><span class="label">Node size:</span><b id="d-size"></b></div>
<div class="stat"><span class="label">ID:</span><span id="d-id" style="font-family:monospace;font-size:12px"></span></div>
</div>

<script>
const graphData={{nodes:{json.dumps(nodes[:2000])},links:{json.dumps(links[:5000])}}};
document.getElementById('loading').style.display='none';

const width=innerWidth,height=innerHeight;
const svg=d3.select("#viz").append("svg").attr("width",width).attr("height",height).attr("viewBox",[0,0,width,height]);

svg.call(d3.zoom().extent([[0,0],[width,height]]).scaleExtent([0.1,4]).on("zoom",e=>g.attr("transform",e.transform)));

const g=svg.append("g");

const simulation=d3.forceSimulation(graphData.nodes)
  .force("charge",d3.forceManyBody().strength(-30))
  .force("center",d3.forceCenter(width/2,height/2))
  .force("link",d3.forceLink(graphData.links).id(d=>d.id).distance(80))
  .force("collide",d3.forceCollide().radius(d=>d.size+5));

const link=g.append("g").selectAll("line").data(graphData.links).join("line")
  .attr("class","link").attr("stroke-width",d=>Math.sqrt(d.weight));

const node=g.append("g").selectAll("circle").data(graphData.nodes).join("circle")
  .attr("class","node").attr("r",d=>d.size)
  .attr("fill",d=>d.color)
  .call(d3.drag().on("start",dragstarted).on("drag",dragged).on("end",dragended));

node.on("click",(e,d)=>{{
  document.getElementById('details').style.display='block';
  document.getElementById('d-title').textContent=d.label;
  document.getElementById('d-pr').textContent=(d.pagerank*1000).toFixed(3);
  document.getElementById('d-size').textContent=d.size;
  document.getElementById('d-id').textContent=d.id;
}});

document.getElementById('close').onclick=()=>document.getElementById('details').style.display='none';

simulation.on("tick",()=>{{
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  node.attr("cx",d=>d.x).attr("cy",d=>d.y);
}});

function dragstarted(e,d){{if(!e.active)simulation.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y}}
function dragged(e,d){{d.fx=e.x;d.fy=e.y}}
function dragended(e,d){{if(!e.active)simulation.alphaTarget(0);d.fx=null;d.fy=null}}
</script>
</body>
</html>'''

# Save
output_file = Path("./graph/index.html")
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Created: {output_file}")
print(f"🌐 Open in browser: open {output_file}")
