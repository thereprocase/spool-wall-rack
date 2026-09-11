"""Standalone regression checks for PlasticShape.integrated_volume."""
from pathlib import Path
import argparse, json, time
import numpy as np
import shapely
from shapely.geometry import Polygon, box

from plastic_shape import PlasticShape


def analytic_fixture():
    raw1, raw2 = box(0, 0, 2, 1), box(1, 0, 3, 2)
    cont1, cont2 = box(0, 0, 3, 1), box(1, 0, 4, 2)
    shape = PlasticShape([(0., 1., raw1, cont1), (1., 3., raw2, cont2)])
    queries = [box(0, 0, 4, 2), box(0, 0, 1, 1), box(1, 0, 2, 1),
               box(2, 0, 4, 3), box(10, 10, 11, 11), Polygon()]
    expected_raw = np.array([10., 1., 3., 4., 0., 0.])
    expected_cont = np.array([15., 1., 3., 9., 0., 0.])
    raw1w = shape.integrated_volume(queries, workers=1)
    raw4w = shape.integrated_volume(queries, workers=4)
    cont = shape.integrated_volume(queries, continuum=True, workers=4)
    assert np.allclose(raw1w, expected_raw, atol=1e-12)
    assert np.allclose(raw4w, expected_raw, atol=1e-12)
    assert np.allclose(cont, expected_cont, atol=1e-12)
    # Overlap is intentionally reported per query, independently.
    separate = np.array([shape.integrated_volume([q], workers=1)[0] for q in queries[:4]])
    assert np.allclose(separate, raw1w[:4], atol=1e-12)
    return {"raw_workers_1":raw1w.tolist(), "raw_workers_4":raw4w.tolist(),
            "continuum_workers_4":cont.tolist(), "expected_raw":expected_raw.tolist(),
            "expected_continuum":expected_cont.tolist(), "overlap_queries_independent":True,
            "status":"PASS"}


def real_reference(root):
    cache = PlasticShape.load(root/"2w-5layers"/"validated-shape")
    reference = shapely.union_all([layer[2] for layer in cache.layers])
    roi = box(130, -37, 160, -19)
    t0=time.perf_counter(); whole=cache.integrated_volume([reference], workers=4); whole_s=time.perf_counter()-t0
    t0=time.perf_counter(); roi_v=cache.integrated_volume([roi], workers=1); roi_s=time.perf_counter()-t0
    assert abs(whole[0]-cache.volume()) < 1e-6
    return {"cache":"g-recheck/2w-5layers/validated-shape",
            "whole_projection_volume_mm3":float(whole[0]), "shape_volume_mm3":float(cache.volume()),
            "whole_projection_abs_error_mm3":float(abs(whole[0]-cache.volume())),
            "roi_box_mm":[130.,-37.,160.,-19.], "roi_volume_mm3":float(roi_v[0]),
            "whole_projection_seconds_workers4":whole_s, "roi_seconds_workers1":roi_s,
            "status":"PASS"}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=Path("analysis/rev-g2/g-recheck")); ap.add_argument("--output",type=Path,default=Path("analysis/rev-g2/validation/integrated-volume-api.json")); args=ap.parse_args()
    report={"analytic_two_slab_fixture":analytic_fixture(),"real_reference":real_reference(args.root),
            "scope":"Exact 2D polygon intersection area integrated over cached Z slabs. Per-query results are independent for overlapping regions; no quadrature, stiffness, strength, or print qualification.","status":"PASS"}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2))

if __name__ == "__main__": main()
