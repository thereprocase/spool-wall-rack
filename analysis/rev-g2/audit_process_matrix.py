"""Read-only audit of the five archived Rev-G2 Orca process variants.

This intentionally audits emitted paths and metadata; it never invokes Orca or
modifies the archived artifacts.  It is a geometry/process audit, not a
calibrated P1S material or print qualification.
"""
from __future__ import annotations

import argparse, hashlib, json, re, zipfile
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CASES = ("2w-5layers", "8w-2layers", "2w-8layers", "2w-2layers", "8w-8layers")
GEOMETRY_FILES = ("body-only.stl", "body-only.step", "dense-chords-and-seats.stl",
                  "dense-chords-and-seats.step", "rib-plane-lower.stl",
                  "rib-plane-lower.step", "rib-plane-upper.stl", "rib-plane-upper.step")

def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def scalar(v):
    if isinstance(v, list):
        return v[0] if len(v) == 1 else v
    return v

def numeric_stats(values):
    """Compact a potentially large exact-value list for the JSON report."""
    a = np.asarray(values, dtype=float)
    if not len(a): return {"min": None, "max": None, "unique_count": 0}
    q = np.quantile(a, [0, .25, .5, .75, 1]).tolist()
    return {"min": float(a.min()), "max": float(a.max()), "unique_count": int(len(np.unique(a))),
            "quantiles_p0_p25_p50_p75_p100": [float(round(x, 6)) for x in q]}

def parse_gcode(path: Path):
    # Machine coordinates are the emitted XY footprint.  Only moves within the
    # printing-object block and with positive E count as deposited paths.
    text = path.read_text(encoding="utf-8", errors="replace")
    pos = np.zeros(3); prev_e = 0.0; relative_e = True; absolute_xyz = True
    role, width, height, z = "Custom", .45, .2, None
    rows = []
    active = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if line.startswith("; printing object"): active = True
        elif line.startswith("; stop printing object"): active = False
        elif line.startswith((";TYPE:", "; FEATURE:")): role = line.split(":", 1)[1].strip()
        elif line.startswith((";WIDTH:", "; LINE_WIDTH:")):
            width = float(line.split(":", 1)[1])
        elif line.startswith((";HEIGHT:", "; LAYER_HEIGHT:")):
            height = float(line.split(":", 1)[1])
        elif line.startswith((";Z:", "; Z_HEIGHT:")):
            z = float(line.split(":", 1)[1])
        code = line.split(";", 1)[0].strip()
        if not code: continue
        cmd = code.split(" ", 1)[0]
        try:
            fields = {k: float(v) for k, v in re.findall(r"([XYZE])([-+\d.eE]+)", code) if v not in ("-", "+", ".", "-.", "+.")}
        except ValueError as exc:
            raise ValueError(f"invalid numeric G-code at {path}:{line_number}: {code}") from exc
        if cmd == "M83": relative_e = True
        elif cmd == "M82": relative_e = False
        elif cmd == "G90": absolute_xyz = True
        elif cmd == "G91": absolute_xyz = False
        elif cmd == "G92":
            if "E" in fields: prev_e = fields["E"]
            for j,k in enumerate("XYZ"):
                if k in fields: pos[j] = fields[k]
            continue
        elif cmd in ("G0", "G1"):
            new = pos.copy()
            for j,k in enumerate("XYZ"):
                if k in fields: new[j] = fields[k] if absolute_xyz else pos[j] + fields[k]
            e = fields.get("E", 0.0)
            extrusion = e if relative_e and "E" in fields else (e - prev_e if "E" in fields else 0.0)
            if "E" in fields: prev_e = prev_e + e if relative_e else e
            if active and extrusion > 0 and np.linalg.norm(new[:2]-pos[:2]) > 1e-8:
                rows.append({"a": pos.copy(), "b": new.copy(), "e": extrusion,
                             "role": role, "width": width, "height": height, "z": z})
            pos = new
    return rows, text

def metadata_field_names(three_mf: Path):
    # Report names only.  Do not serialize metadata values, paths, authors, or
    # other potentially identifying information from a project archive.
    names = set(); count = 0
    with zipfile.ZipFile(three_mf) as z:
        for n in z.namelist():
            if not (n.lower().endswith((".model", ".xml", ".config", ".json"))): continue
            try: raw = z.read(n).decode("utf-8", "ignore")
            except Exception: continue
            for key in re.findall(r"(?:[<\s]|\")([A-Za-z_][A-Za-z0-9_.:-]*(?:path|file|user|author|account|creator|source)[A-Za-z0-9_.:-]*)(?:[=\s:]|\")", raw, re.I):
                names.add(key)
                count += 1
    return {"field_names": sorted(names), "occurrence_count": count, "values_redacted": True}

def model_settings_summary(three_mf: Path):
    """Extract only process facts needed for this audit from model_settings."""
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(three_mf) as z:
        root = ET.fromstring(z.read("Metadata/model_settings.config"))
    out = {"object_process": {}, "parts": []}
    obj = root.find("object")
    if obj is None: return out
    for m in obj.findall("metadata"):
        if m.get("key") in {"wall_loops", "top_shell_layers", "bottom_shell_layers", "top_shell_thickness", "bottom_shell_thickness", "sparse_infill_density", "wall_generator"}:
            out["object_process"][m.get("key")] = m.get("value")
    for part in obj.findall("part"):
        row = {"id": part.get("id"), "subtype": part.get("subtype")}
        for m in part.findall("metadata"):
            key = m.get("key")
            if key == "sparse_infill_density": row["sparse_infill_density"] = m.get("value")
            elif key == "source_file": row["source_file_basename"] = Path(m.get("value", "")).name
        out["parts"].append(row)
    return out

def audit_case(case_dir: Path, expected_walls: int, expected_skin: int, reference: Path):
    work = case_dir / ".work" / f"audit-{expected_walls}w"
    settings = json.loads((work / "effective-settings.json").read_text(encoding="utf-8"))
    result = json.loads((work / "result.json").read_text(encoding="utf-8"))
    rows, gcode = parse_gcode(work / "plate_1.gcode")
    settings_keys = ("wall_loops", "top_shell_layers", "bottom_shell_layers", "top_shell_thickness",
                     "bottom_shell_thickness", "sparse_infill_density", "ensure_vertical_shell_thickness",
                     "wall_generator", "outer_wall_line_width", "inner_wall_line_width",
                     "internal_solid_infill_line_width", "top_surface_line_width", "nozzle_diameter",
                     "printable_area", "bed_exclude_area")
    actual = {k: scalar(settings.get(k)) for k in settings_keys if k in settings}
    model_summary = model_settings_summary(work/"audit.3mf")
    expected_thickness = expected_skin * 0.2
    assert str(actual.get("wall_loops")) == str(expected_walls) and str(actual.get("top_shell_layers")) == str(expected_skin) and str(actual.get("bottom_shell_layers")) == str(expected_skin)
    assert abs(float(actual.get("top_shell_thickness")) - expected_thickness) < 1e-6 and abs(float(actual.get("bottom_shell_thickness")) - expected_thickness) < 1e-6
    assert str(actual.get("sparse_infill_density")) in {"0", "0%", "0.0%"}
    assert model_summary["object_process"].get("sparse_infill_density") == "0%"
    helper_parts = [p for p in model_summary["parts"] if p.get("subtype") == "modifier_part"]
    assert len(helper_parts) == 3 and all(p.get("sparse_infill_density") == "100%" for p in helper_parts)
    widths = np.array([r["width"] for r in rows]); heights = np.array([r["height"] for r in rows])
    all_xy = np.array([p for r in rows for p in ((r["a"][0], r["a"][1]), (r["b"][0], r["b"][1]))]).reshape(-1,2)
    radius = widths.max()/2 if len(widths) else 0
    envelope = {"xmin_mm": float(all_xy[:,0].min()-radius), "xmax_mm": float(all_xy[:,0].max()+radius),
                "ymin_mm": float(all_xy[:,1].min()-radius), "ymax_mm": float(all_xy[:,1].max()+radius)} if len(all_xy) else {}
    outside = [r for r in rows if min(r["a"][0],r["b"][0])-r["width"]/2 < 0 or max(r["a"][0],r["b"][0])+r["width"]/2 > 256 or min(r["a"][1],r["b"][1])-r["width"]/2 < 0 or max(r["a"][1],r["b"][1])+r["width"]/2 > 256]
    excluded = [r for r in rows if max(r["a"][0],r["b"][0])+r["width"]/2 > 0 and min(r["a"][0],r["b"][0])-r["width"]/2 < 18 and max(r["a"][1],r["b"][1])+r["width"]/2 > 0 and min(r["a"][1],r["b"][1])-r["width"]/2 < 28]
    bridge = [r for r in rows if "bridge" in r["role"].lower()]
    thick_bridge = [r for r in bridge if r["height"] > .2001]
    source_hashes = {f: sha(case_dir/f) for f in GEOMETRY_FILES}
    reference_hashes = {f: sha(reference/f) for f in GEOMETRY_FILES if (reference/f).exists()}
    hash_matches = {f: source_hashes[f] == reference_hashes.get(f) for f in GEOMETRY_FILES}
    assert all(hash_matches.values())
    assert not outside and not excluded
    return {"case": case_dir.name, "work": str(work.relative_to(ROOT)).replace("\\", "/"),
            "expected": {"wall_loops": expected_walls, "top_bottom_layers": expected_skin},
            "effective_settings": actual, "settings_match_expected": actual.get("wall_loops") == str(expected_walls) and actual.get("top_shell_layers") == str(expected_skin) and actual.get("bottom_shell_layers") == str(expected_skin),
            "slice_result": {"return_code": result.get("return_code"), "error_string": result.get("error_string"), "layer_height": result.get("layer_height"), "sparse_infill_density": result.get("sparse_infill_density"), "wall_loops": result.get("wall_loops")},
            "gcode": {"sha256": sha(work/"plate_1.gcode"), "extrusion_moves": len(rows), "roles": sorted(set(r["role"] for r in rows)), "height_values_mm": sorted(set(round(r["height"],6) for r in rows)), "width_stats_mm": numeric_stats(widths), "bridge_moves": len(bridge), "bridge_height_values_mm": sorted(set(round(r["height"],6) for r in bridge)), "bridge_width_values_mm": sorted(set(round(r["width"],6) for r in bridge)), "thick_bridge_moves_height_gt_0p2001": len(thick_bridge), "thick_bridge_height_values_mm": sorted(set(round(r["height"],6) for r in thick_bridge)), "thick_bridge_width_values_mm": sorted(set(round(r["width"],6) for r in thick_bridge)), "bridge_policy": "Count plastic; zero stiffness, strength, and bonded-connection credit."},
            "P1S_256mm_bed": {"envelope_with_path_width_mm": envelope, "outside_bed_path_count": len(outside), "bed_exclusion_rect_xy_mm": [0,0,18,28], "bed_exclusion_intersection_path_count": len(excluded)},
            "geometry_hashes": {"case": source_hashes, "matches_rev_g_source_package": hash_matches},
            "3mf_model_settings": model_summary,
            "3mf_metadata_field_names_only": metadata_field_names(work/"audit.3mf"),
            "profile_distinction": "Neutral geometry audit machine/process settings; not a P1S PETG or ASA calibrated material profile."}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path("analysis/rev-g2/validation/process-matrix.json"))
    ap.add_argument("--p1s-profile", type=Path, help="Optional installed Orca P1S machine JSON; selected fields only are reported.")
    args = ap.parse_args()
    base = ROOT / "designs/rev-g2/g-recheck"; reference = ROOT / "designs/rev-g"
    rows = []
    for case in CASES:
        m = re.fullmatch(r"([28])w-([258])layers", case)
        rows.append(audit_case(base/case, int(m.group(1)), int(m.group(2)), reference))
    official = args.p1s_profile
    official_keys = {}
    if official.exists():
        raw = json.loads(official.read_text(encoding="utf-8"))
        for key in ("nozzle_diameter", "printable_area", "printable_height", "bed_exclude_area", "printer_model", "name"):
            if key in raw: official_keys[key] = scalar(raw[key])
    out = {"status": "AUDIT_ONLY", "root": "designs/rev-g2/g-recheck", "cases": rows,
           "official_P1S_profile_selected_keys": official_keys,
           "official_P1S_profile_sha256": sha(official) if official and official.exists() else None,
           "bed_assumption": "P1S nominal 256 x 256 mm; exclusion rectangle 0..18 x 0..28 mm used for envelope audit.",
           "limitations": ["Neutral machine baseline is geometry-only and not a calibrated P1S PETG/ASA profile.", "G-code footprint includes declared path-width envelopes; no material qualification is inferred.", "No reslicing, installation, packaging, or source edits performed."]}
    outp = args.output if args.output.is_absolute() else ROOT/args.output
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(outp), "cases": len(rows), "outside_bed": [r["P1S_256mm_bed"]["outside_bed_path_count"] for r in rows]}, indent=2))

if __name__ == "__main__": main()
