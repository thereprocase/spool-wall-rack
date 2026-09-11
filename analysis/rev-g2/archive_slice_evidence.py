"""Create deterministic, privacy-scanned Rev-G2 slice evidence archives.

Raw input members are copied byte-for-byte.  The script never reslices or
rewrites the 3MF/G-code/settings/result files and records only relative paths.
"""
from __future__ import annotations
import argparse, hashlib, json, re, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
CASES = ("2w-5layers", "8w-2layers", "2w-8layers", "2w-2layers", "8w-8layers")
MEMBERS = ("plate_1.gcode", "audit.3mf", "effective-settings.json", "result.json")
GEOMETRY = ("body-only.stl", "body-only.step", "dense-chords-and-seats.stl", "dense-chords-and-seats.step",
            "rib-plane-lower.stl", "rib-plane-lower.step", "rib-plane-upper.stl", "rib-plane-upper.step")
SENSITIVE_KEY = re.compile(r"(?:path|file|author|email|user(?:name)?|token|secret|password|credential|account|home|cwd|directory)", re.I)
EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ABS_PATH = re.compile(rb"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|\\\\[A-Za-z0-9_.$-]+[\\/])", re.I)
UNIX_PRIVATE_PATH = re.compile(rb"(?:^|[ \t\r\n=\"'(])/(?:home|Users|mnt/[A-Za-z]|tmp|var|private|opt|workspace|root)/", re.I | re.M)
TOKEN = re.compile(rb"(?:bearer\s+[A-Za-z0-9._~-]{12,}|(?:api[_-]?key|access[_-]?token|secret|password)\s*[=:]\s*[^\s\"']{8,})", re.I)

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()

def scan_blob(member: str, data: bytes):
    """Return findings as field/member/count only; never return matched values."""
    findings = {}
    def add(field, count=1):
        key = (field, member)
        findings[key] = findings.get(key, 0) + count
    # A 3MF is a binary ZIP; scanning its compressed bytes creates random
    # false positives. Its textual members are scanned below instead.
    if not member.endswith(".3mf"):
        if EMAIL.findall(data): add("email_or_authoremail", len(EMAIL.findall(data)))
        if ABS_PATH.findall(data): add("local_or_absolute_path", len(ABS_PATH.findall(data)))
        if UNIX_PRIVATE_PATH.findall(data): add("unix_private_absolute_path", len(UNIX_PRIVATE_PATH.findall(data)))
        if TOKEN.findall(data): add("token_or_secret_like_value", len(TOKEN.findall(data)))
    # Parse structured members to identify the exact metadata key, but retain
    # neither key values nor text snippets in the output.
    if member.endswith(".3mf"):
        try:
            with zipfile.ZipFile(__import__("io").BytesIO(data)) as archive:
                for nested in archive.namelist():
                    if not nested.lower().endswith((".xml", ".config", ".json", ".model")): continue
                    nested_data = archive.read(nested)
                    if EMAIL.findall(nested_data): add(f"{nested}:email_or_authoremail", len(EMAIL.findall(nested_data)))
                    if ABS_PATH.findall(nested_data): add(f"{nested}:local_or_absolute_path", len(ABS_PATH.findall(nested_data)))
                    if UNIX_PRIVATE_PATH.findall(nested_data): add(f"{nested}:unix_private_absolute_path", len(UNIX_PRIVATE_PATH.findall(nested_data)))
                    if TOKEN.findall(nested_data): add(f"{nested}:token_or_secret_like_value", len(TOKEN.findall(nested_data)))
                    try:
                        root = ET.fromstring(nested_data)
                        for el in root.iter():
                            for key, value in el.attrib.items():
                                if SENSITIVE_KEY.search(key) and (EMAIL.search(value.encode()) or ABS_PATH.search(value.encode()) or TOKEN.search(value.encode())):
                                    add(f"{nested}:{key}")
                    except Exception: pass
        except zipfile.BadZipFile: add("invalid_3mf_archive")
    elif member.endswith(".json"):
        try:
            obj = json.loads(data.decode("utf-8"))
            def walk(x):
                if isinstance(x, dict):
                    for key, value in x.items():
                        if SENSITIVE_KEY.search(str(key)) and isinstance(value, (str, int, float)):
                            vb = str(value).encode()
                            if EMAIL.search(vb) or ABS_PATH.search(vb) or TOKEN.search(vb): add(str(key))
                        walk(value)
                elif isinstance(x, list):
                    for value in x: walk(value)
            walk(obj)
        except (UnicodeDecodeError, json.JSONDecodeError): add("invalid_json")
    return [{"field": f, "member": m, "count": c} for (f, m), c in sorted(findings.items())]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-root", type=Path, default=Path("designs/rev-g2/g-recheck"))
    ap.add_argument("--report", type=Path, default=Path("analysis/rev-g2/validation/slice-archive-audit.json"))
    args = ap.parse_args()
    base = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    case_reports = []
    for case in CASES:
        case_dir = base / case
        work = case_dir / ".work" / ("audit-2w" if case.startswith("2w") else "audit-8w")
        blobs = {member: (work / member).read_bytes() for member in MEMBERS}
        findings = [f for member, data in blobs.items() for f in scan_blob(member, data)]
        row = {"case": case, "source_root": str(case_dir.relative_to(ROOT)).replace("\\", "/"),
               "candidate_members": list(MEMBERS), "offending_fields_members_counts": findings,
               "status": "BLOCKED_PRIVATE_DATA" if findings else "PASS"}
        if findings:
            case_reports.append(row); continue
        source_files = []
        for name in GEOMETRY:
            case_hash = sha_file(case_dir / name)
            published = ROOT / "designs/rev-g" / name
            published_hash = sha_file(published)
            assert case_hash == published_hash, f"case geometry differs from published Rev-G source: {case}/{name}"
            source_files.append({"path": f"designs/rev-g/{name}", "sha256": published_hash})
        manifest = {"case": case, "source_root": row["source_root"], "source_geometry": source_files,
                    "evidence_members": [{"path": member, "sha256": sha_bytes(blobs[member]), "bytes": len(blobs[member])} for member in MEMBERS],
                    "raw_member_policy": "Copied byte-for-byte; no reserialization.", "privacy_scan": "PASS; no offending field/member/count findings."}
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        archive_path = case_dir / "slice-evidence.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
            for member in sorted(MEMBERS + ("source-hash-manifest.json",)):
                data = manifest_bytes if member == "source-hash-manifest.json" else blobs[member]
                info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o600 << 16
                out.writestr(info, data)
        row.update({"status": "PASS", "archive": str(archive_path.relative_to(ROOT)).replace("\\", "/"), "archive_sha256": sha_file(archive_path), "archive_bytes": archive_path.stat().st_size,
                    "source_geometry": source_files, "member_hashes": manifest["evidence_members"], "zip_members": sorted(MEMBERS + ("source-hash-manifest.json",))})
        case_reports.append(row)
    report = {"status": "PASS" if all(x["status"] == "PASS" for x in case_reports) else "REVIEW_BLOCKED_CASES", "cases": case_reports,
              "raw_inputs_preserved": True, "private_values_emitted": False, "archive_policy": "Five compact deterministic archives; geometry referenced by relative source hashes."}
    report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "cases": [{"case": x["case"], "status": x["status"], "archive_bytes": x.get("archive_bytes")} for x in case_reports]}, indent=2))

if __name__ == "__main__": main()
