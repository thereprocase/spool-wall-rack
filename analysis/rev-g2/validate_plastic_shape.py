"""Independent checks for cached slicer plastic occupancy.

The oracle below deliberately uses G-code segments and their emitted widths,
not the polygon implementation in plastic_shape.py.  It is a tolerance audit
for occupancy and integrated thickness; it is not a mechanics validation.
"""
from pathlib import Path
import argparse, json, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shapely
from matplotlib.patches import Patch

from plastic_shape import PlasticShape, read_paths


def capsule_distance(points, paths, widths):
    """Minimum signed distance to variable-width segment capsules."""
    points = np.asarray(points, float)
    if len(paths) == 0 or len(points) == 0:
        return np.full(len(points), np.inf)
    # Candidate query uses the maximum radius, then every candidate receives
    # its own exact point-to-segment distance and emitted width correction.
    tree = shapely.STRtree(shapely.linestrings(paths))
    maxr = float(np.max(widths)/2+.005)
    out = np.full(len(points), np.inf)
    a, b = paths[:, 0], paths[:, 1]
    ab, den = b-a, np.sum((b-a)*(b-a), axis=1)
    for i, point in enumerate(shapely.points(points)):
        candidates = np.asarray(tree.query(point, predicate="dwithin", distance=maxr), dtype=int)
        if not len(candidates):
            continue
        ap = point.coords[0]-a[candidates]
        u = np.clip(np.divide(np.sum(ap*ab[candidates], axis=1), den[candidates],
                              out=np.zeros(len(candidates)), where=den[candidates]>0), 0, 1)
        q = a[candidates]+u[:, None]*ab[candidates]
        out[i] = np.min(np.linalg.norm(point.coords[0]-q, axis=1)-widths[candidates]/2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="analysis/rev-g2/g-recheck cache root")
    ap.add_argument("--source-root", type=Path, default=None, help="designs/rev-g2/g-recheck source root")
    ap.add_argument("--seed", type=int, default=20260911)
    ap.add_argument("--samples", type=int, default=5000)
    ap.add_argument("--plot-only", action="store_true", help="rerender sections from existing caches")
    args = ap.parse_args()
    if args.plot_only:
        render_sections(args.root, sorted(p.name for p in args.root.iterdir() if (p/"validated-shape").is_dir()), args.root.parent/"validation")
        return
    rng = np.random.default_rng(args.seed)
    rows = []
    source_root = (args.source_root or args.root).resolve()
    sources = sorted(source_root.glob("*/.work/audit-*"))
    if not sources:
        raise RuntimeError(f"no audit slices found under {source_root}")
    print(f"validating {len(sources)} slices", flush=True)
    for src in sources:
        case = src.parent.parent.name
        out = args.root / case / "validated-shape"
        tload = time.perf_counter(); cache = PlasticShape.load(out); load_s = time.perf_counter()-tload
        data, footer = read_paths(src)
        structural = data["structural"]
        assert not np.any(data["role"] == "Sparse infill")
        thick = ~structural
        assert np.all(data["height"][thick] > .2001)
        # Use structural paths only, matching the cache contract.
        pth, wid, hei, top = (data[k][structural] for k in ("paths", "width", "height", "top"))
        lo = np.min(pth.reshape(-1, 2), axis=0)-wid.max()
        hi = np.max(pth.reshape(-1, 2), axis=0)+wid.max()
        n = args.samples
        # Mix global, requested hotspot, and near-active-path samples so the
        # occupancy audit has substantial positive and boundary populations.
        ng, nh = n//2, n//5
        na = n-ng-nh
        xy = np.vstack((rng.uniform(lo, hi, (ng, 2)),
                        rng.uniform([130, -37], [160, -19], (nh, 2))))
        chosen = rng.integers(0, len(pth), na)
        tangent = pth[chosen, 1]-pth[chosen, 0]
        tangent /= np.linalg.norm(tangent, axis=1)[:, None]
        normal = np.column_stack((-tangent[:,1], tangent[:,0]))
        xy = np.vstack((xy, (pth[chosen,0]+rng.random((na,1))*tangent*np.linalg.norm(pth[chosen,1]-pth[chosen,0],axis=1)[:,None]
                             +rng.uniform(-.6,.6,(na,1))*normal)))
        zlo, zhi = float(np.min(data["top"]-data["height"])), float(np.max(data["top"]))
        xyz = np.column_stack((xy, rng.uniform(zlo, zhi, n)))
        t0 = time.perf_counter(); actual = cache.contains(xyz); contains_s = time.perf_counter()-t0
        # A segment is active at z if its slab contains the query.
        k = np.searchsorted(cache.z1, xyz[:, 2], side="right")
        oracle = np.zeros(n, bool)
        oracle_margin = np.full(n, np.inf)
        for j in np.unique(k):
            if j >= len(cache.layers): continue
            sel = k == j
            mid = (cache.layers[j][0]+cache.layers[j][1])/2
            active = (top > mid) & (top-hei < mid)
            dd = capsule_distance(xy[sel], pth[active], wid[active])
            oracle[sel] = dd <= 0
            oracle_margin[sel] = dd
        mismatch = actual != oracle
        band = np.abs(oracle_margin) <= .005
        z_mismatch_outside_band = int(np.sum(mismatch & ~band))
        # Independent thickness oracle at a smaller set of points.
        qxy = np.vstack((rng.uniform(lo, hi, (max(500, n//5), 2)),
                         rng.uniform([130, -37], [160, -19], (max(500, n//5), 2))))
        t0 = time.perf_counter(); thick_actual = cache.equivalent_thickness(qxy); thickness_s = time.perf_counter()-t0
        thick_oracle = np.zeros(len(qxy)); thickness_band = np.zeros(len(qxy))
        for z0, z1, _, _ in cache.layers:
            mid=(z0+z1)/2
            active=(top > mid)&(top-hei < mid)
            if np.any(active):
                margin = capsule_distance(qxy, pth[active], wid[active])
                thick_oracle += (margin <= 0)*(z1-z0)
                thickness_band += (np.abs(margin) <= .005)*(z1-z0)
        td = np.abs(thick_actual-thick_oracle)
        assert np.all(td <= thickness_band+1e-7)
        rows.append({"case":case, "paths":int(len(data["paths"])),
            "structural_paths":int(structural.sum()), "thick_bridge_segments":int(thick.sum()),
            "sparse_infill_segments":int(np.sum(data["role"]=="Sparse infill")),
            "footer_volume_mm3":footer["Orca_footer_volume_mm3"],
            "raw_union_volume_mm3":cache.volume(),
            "credited_extrusion_volume_mm3":footer["structurally_credited_extrusion_volume_mm3"],
            "thick_bridge_volume_mm3":footer["sacrificial_thick_bridge_extrusion_volume_mm3"],
            "cache_volume_mm3":cache.volume(), "cache_load_seconds":load_s, "contains_query_seconds":contains_s,
            "thickness_query_seconds":thickness_s, "occupancy_samples":n,
            "occupancy_mismatch":int(mismatch.sum()),
            "occupancy_mismatch_outside_0p005mm_band":z_mismatch_outside_band,
            "thickness_max_error_mm":float(td.max()), "thickness_mean_error_mm":float(td.mean()),
            "boundary_uncertainty_mm":.005, "occupancy_positive_oracle_samples":int(oracle.sum()),
            "occupancy_boundary_samples":int(np.sum(np.abs(oracle_margin)<=.005)),
            "policy":"Thick bridges count as spent plastic and are excluded from cache structural occupancy; no strength claim."})
        print(f"completed {case}", flush=True)
    report={"seed":args.seed,"cases":rows,"status":"independent capsule and thickness oracle checks; mechanics unvalidated"}
    out=args.root.parent/"validation"
    out.mkdir(parents=True, exist_ok=True)
    (out/"matrix-shape-validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    render_sections(args.root, [r["case"] for r in rows], out)


def render_sections(root, labels, out):
    """Render filled cross-sections without rerunning the expensive oracle."""
    # Cross-section matrix: each column is a wall/skin schedule and each row
    # is a representative layer. The requested throat hotspot is highlighted.
    zs=(.9, 3.1, 8.9)
    fig, axes=plt.subplots(3, 5, figsize=(15, 8), squeeze=False)
    for c, case in enumerate(labels):
        cache=PlasticShape.load(root/case/"validated-shape")
        for rr, z in enumerate(zs):
            ax=axes[rr,c]; geom=cache.section(z)
            for poly in getattr(geom, "geoms", [geom]):
                if poly.is_empty: continue
                x,y=poly.exterior.xy; ax.fill(x,y,color="#4c78a8",alpha=.9,linewidth=0)
                for ring in poly.interiors:
                    x,y=ring.xy; ax.fill(x,y,color="white",linewidth=0)
                x,y=poly.exterior.xy; ax.plot(x,y,color="#1f3d5a",lw=.35)
                for ring in poly.interiors:
                    x,y=ring.xy; ax.plot(x,y,color="#1f3d5a",lw=.25)
            ax.set_xlim(130,160); ax.set_ylim(-37,-19); ax.set_aspect("equal")
            ax.grid(alpha=.15); ax.set_title(f"{case}\nz={z:g} mm",fontsize=8)
    fig.suptitle("Rev-G2 sliced structural cross-sections (hotspot x=130..160, y=-37..-19)")
    fig.legend(handles=[Patch(facecolor="#4c78a8",label="credited structural material"),
                        Patch(facecolor="white",edgecolor="#1f3d5a",label="void")],
               loc="lower center", ncol=2, frameon=False)
    fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig(out/"matrix-shape-sections.png",dpi=160); plt.close(fig)

if __name__ == "__main__": main()
