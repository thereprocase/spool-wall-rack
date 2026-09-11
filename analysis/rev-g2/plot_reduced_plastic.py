"""Plot the final exact reduced-plastic h1 field with h2 comparison values."""
from pathlib import Path
import argparse, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri


def load(root, name):
    d = root/(name+".npz")
    j = json.loads((root/(name+".json")).read_text(encoding="utf-8"))
    z = np.load(d)
    p, t, u, stress = z["p"], z["t"], z["u"], z["stress"]
    principal = np.linalg.eigvalsh(stress.transpose(2, 0, 1))[:, 1]
    disp = np.linalg.norm(u, axis=1)[t].mean(axis=1)
    return {"json":j, "p":p, "t":t, "thickness":z["element_mean_thickness"],
            "displacement":disp, "stress":principal, "tri":mtri.Triangulation(p[:,0],p[:,1],t)}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=Path("analysis/rev-g2/reduced-plastic")); args=ap.parse_args()
    h1, h2 = load(args.root, "2w-5layers-exact-h1"), load(args.root, "2w-5layers-exact-h2")
    fields=[("actual material mean thickness (mm)","thickness","viridis"),
            ("resultant displacement (mm)","displacement","magma"),
            ("maximum principal stress (MPa)","stress","plasma")]
    fig, axes=plt.subplots(1,3,figsize=(18,6),constrained_layout=True)
    summary={"fields":{},"source":"final exact fields only; all finite triangles retained","status":"PASS"}
    for ax,(label,key,cmap) in zip(axes,fields):
        a,b=h1[key],h2[key]
        assert np.isfinite(a).all() and np.isfinite(b).all()
        vmin,vmax=float(min(a.min(),b.min())),float(max(a.max(),b.max()))
        m=ax.tripcolor(h1["tri"],facecolors=a,shading="flat",cmap=cmap,vmin=vmin,vmax=vmax)
        fig.colorbar(m,ax=ax,label=label,pad=.02)
        ax.set_aspect("equal"); ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)")
        ax.set_title("2w-5layers exact h1\n"+label)
        ax.text(.02,.02,f"h1 min/max: {a.min():.4g} / {a.max():.4g}\nh2 min/max: {b.min():.4g} / {b.max():.4g}",transform=ax.transAxes,fontsize=8,va="bottom",bbox={"facecolor":"white","alpha":.8,"edgecolor":"none"})
        summary["fields"][key]={"h1_min":float(a.min()),"h1_max":float(a.max()),"h1_mean":float(a.mean()),"h2_min":float(b.min()),"h2_max":float(b.max()),"h2_mean":float(b.mean()),"common_scale":[vmin,vmax],"h1_triangles":int(len(a)),"h2_triangles":int(len(b))}
    fig.suptitle("Reduced diagnostic: exact integrated printed material; raw full fields",fontsize=14)
    fig.savefig(args.root/"exact-recheck.png",dpi=180); plt.close(fig)
    (args.root/"exact-recheck.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")

if __name__ == "__main__": main()
