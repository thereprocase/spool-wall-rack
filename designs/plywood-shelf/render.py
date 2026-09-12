"""Render the exported CAD directly; no generated or substituted product geometry."""
from pathlib import Path
import json
import cadquery as cq
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"exports"
P=json.loads((ROOT/"parameters.json").read_text())
left=cq.importers.importStep(str(OUT/"left-installed.step"))
right=cq.importers.importStep(str(OUT/"right-installed.step"))
S=P["stud_spacing"]
W=P["body_width"]
ply=(cq.Workplane("XY").box(P["shelf_depth"],P["plywood_thickness"],
      S-W-2*P["plywood_clearance"],centered=False)
      .translate((P["rear_stop_depth"]+P["plywood_clearance"],0,
                  W+P["plywood_clearance"])))
BG="#f5f3ee"
INK="#273a42"
plt.rcParams.update({"font.family":"DejaVu Sans","text.color":INK,"font.size":12})

def mesh(obj,color):
    verts,faces=obj.val().tessellate(0.2,0.12)
    v=np.array([[q.z,q.x,q.y] for q in verts])
    f=np.array(faces,dtype=int)
    tris=v[f]
    n=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0])
    n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
    light=np.array([.4,.3,1.0]);light/=np.linalg.norm(light)
    lum=.6+.4*np.abs(n@light)  # OCC tessellation may reverse face winding
    colors=np.clip(np.array(to_rgb(color))[None,:]*lum[:,None],0,1)
    return tris,colors,v

def view(ax,objects,elev=23,azim=55,zoom=1):
    vertices=[]
    for obj,color in objects:
        tris,colors,v=mesh(obj,color)
        ax.add_collection3d(Poly3DCollection(tris,facecolors=colors,
                                            edgecolors="none",linewidths=0,zsort="average"))
        vertices.append(v)
    v=np.concatenate(vertices)
    lo=v.min(axis=0);hi=v.max(axis=0)
    span=hi-lo
    pad=np.maximum(span*.04,3)
    ax.set_xlim(lo[0]-pad[0],hi[0]+pad[0])
    ax.set_ylim(lo[1]-pad[1],hi[1]+pad[1])
    ax.set_zlim(lo[2]-pad[2],hi[2]+pad[2])
    ax.set_box_aspect(span+2*pad,zoom=zoom)
    ax.set_proj_type("ortho")
    ax.view_init(elev=elev,azim=azim)
    ax.set_axis_off()
    ax.set_facecolor(BG)

def figure(title,subtitle):
    fig=plt.figure(figsize=(12,7.5),facecolor=BG)
    fig.text(.04,.945,title,fontsize=22,weight="bold")
    fig.text(.04,.895,subtitle,fontsize=11)
    fig.text(.04,.028,"Actual exported CAD • first prototype • unsliced and not load-qualified",
             fontsize=10,color="#61737a")
    return fig

fig=figure("Triangles above. Plywood on lower ledges.",
           "14 in deep × 30.70 in long plywood shown • 32 in stud centres • 3/4 in plywood")
ax=fig.add_axes([.02,.12,.96,.73],projection="3d")
view(ax,[(left,"#517e88"),(right.translate((0,0,S)),"#517e88"),(ply,"#d2b07a")],
     elev=18,azim=61,zoom=1)
fig.text(.05,.09,"Bracket projection: 10.24 in",fontsize=12)
fig.text(.57,.09,"Plywood extends 4.18 in beyond the arms",fontsize=12)
fig.savefig(OUT/"shelf-assembly.png",dpi=180,facecolor=BG)
plt.close(fig)

fig=figure("Left and right • matching triangular bodies",
           "Side triangles rise above the plywood • inward-facing lower ledges carry the shelf")
ax=fig.add_axes([.0,.12,.5,.72],projection="3d")
view(ax,[(left,"#517e88")],elev=25,azim=53)
ax=fig.add_axes([.5,.12,.5,.72],projection="3d")
view(ax,[(right,"#517e88")],elev=25,azim=127)
fig.text(.23,.085,"LEFT",weight="bold",fontsize=15)
fig.text(.72,.085,"RIGHT",weight="bold",fontsize=15)
fig.savefig(OUT/"bracket-pair.png",dpi=180,facecolor=BG)
plt.close(fig)

# Longitudinal section through the screw axes, removing the near half only.
cut=(cq.Workplane("XY").box(500,500,W,centered=False)
     .translate((-50,-250,W/2)))
section=left.cut(cut)
fig=figure("Section through the three stud screws",
           "Near half removed to expose the long access tunnels and the 8 mm wall bearing lands")
ax=fig.add_axes([.0,.15,.72,.7],projection="3d")
view(ax,[(section,"#b28157")],elev=10,azim=8)
fig.text(.73,.68,"Main design concern",weight="bold",fontsize=14)
fig.text(.73,.60,"Lowest screw needs\nabout 230 mm of driver reach.",fontsize=12,linespacing=1.5)
fig.text(.73,.43,"The holes are reachable in CAD,\nbut this is awkward to install.",fontsize=12,linespacing=1.5)
fig.text(.73,.26,"A shorter, open access pocket\nis worth exploring.",fontsize=12,linespacing=1.5)
fig.savefig(OUT/"screw-access-section.png",dpi=180,facecolor=BG)
plt.close(fig)
