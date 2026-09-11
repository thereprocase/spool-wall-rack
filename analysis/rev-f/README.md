# Rev F — numerical checkpoint and unresolved constraints

**September 10, 2026: exploration paused for publication. No candidate passes
the requested full-bracket 4× fracture screen. Evolutionary optimization is
queued for the next sprint and has not been implemented.**

[Current CAD and rendered helpers](../../designs/rev-f/README.md) ·
[Next sprint](../../NEXT-SPRINT.md) · [All extracted 3D metrics](checkpoint-metrics.json).

## Objective and what is complete

Minimize actual printed mass within **5 mm total loaded movement**, **1 mm
change per 1.25 kg spool** and a requested **nominal fracture factor of safety
of four**, reporting stiffness per gram. The 12 kg / 117.72 N reference and
1.0 GPa effective-creep-modulus planning case are retained. E13 stiffness is a
reference only; earlier baseline-matching sweeps are historical experiments.

The fixed Rev F body has two angular windows while preserving E13's outer
outline and functional interfaces. The three-wall shaped-plane handoff and
four-wall full-plane handoff pass CAD/modifier/toolpath checks. Five 3D fields
pass independently assembled residual, force and moment checks below 1e-6;
that numerical equilibrium does not establish strength or physical performance.
Sparse infill has zero structural credit throughout.

| Candidate | Actual Orca volume | Neutral mass at 1.24 g/cm³ | Front movement, E = 1 GPa | Raw 3D tensile peak | 40.5 MPa / peak |
|---|---:|---:|---:|---:|---:|
| E13 eight-wall reference, h1 | 134.77 cm³ | 167.11 g | 2.148 mm | See E13 hotspot audit | Not qualified |
| F three-wall shaped, h2 | 121.95 cm³ | 151.21 g | 2.191 mm | 51.685 MPa | 0.78 — fails |
| F four-wall full, h1 | 118.57 cm³ | 147.02 g | 2.156 mm | 17.598 MPa | 2.30 — fails |
| F light one-wall full, h2 | **Unsliced** | **87.81 g proxy** | 3.582 mm | 47.417 MPa | 0.85 — fails |

The four-wall slice uses 12.0% less plastic than E13; at matched h1 its front
movement is only 0.40% larger. Three-wall h2 movement should be compared with
E13 h2, 2.067 mm, rather than treating different meshes as identical resolution.
[E13 3D results](../e13/RESULTS.md) · [E13 hotspot audit](../e13/HOTSPOTS.md).

The 40.5 MPa screen uses the published typical printed-Z tensile value from
[PolyLite PLA's TDS](https://polymaker.com/wp-content/uploads/lana-downloads/PolyLite-PLA_TDS_EN_V5.4.pdf)
as a conservative scalar input; 40.5/4 = **10.125 MPa**. It is not a qualified
allowable for the actual part, filament process, temperature or lifetime.
The isotropic model does not resolve printed orthotropy or fracture mechanics.
Failure of this screen is retained; a percentile stress or reduced model is
not substituted to declare success.

## Three-level four-wall refinement

| Maximum mesh size | Tetrahedra | Front movement | Raw maximum tensile principal stress | Material volume above 10.125 MPa |
|---:|---:|---:|---:|---:|
| 2.0 mm | 190,361 | 2.0625 mm | 30.571 MPa | 0.05496 mm³ |
| 1.5 mm | 330,547 | 2.1070 mm | 21.185 MPa | 0.04222 mm³ |
| 1.0 mm | 726,544 | 2.1565 mm | 17.598 MPa | 0.01064 mm³ |

Front movement changes 2.35% from h1.5 to h1; raw peak stress is still
mesh-sensitive. At h1 its peak cell lies at installed (21.639, 30.885, 8.863) mm
near the lower access/core junction, with volume 0.00003152 mm³. Small cell
volume alone does not prove a stress artifact. All finite stress cells remain
in the results. Numerical-degeneracy cleanup is separately recorded; the h1
mesh removes only two numerically zero-volume cells totaling 1.91e-14 mm³.

The [four-wall archive](studies/full-plane-4w/) contains all three solution
fields, result JSON, mesh-quality audits and exact candidate parameters. Its
[CAD/slicing handoff](../../designs/rev-f/studies/full-plane-4w/README.md) is
experimental despite its completed manufacturing checks.

## Light candidate: why the search cannot trust 2D strength alone

The one-wall candidate has 0.8 mm skins/planes, 1.8 mm lower/diagonal dense
bands, 4 mm inner-seat reinforcement, 5% sparse infill and tunnel collars/
saddles. Its reduced screen predicts **87.81 g**, front movement about 3.44 mm
and a nominal strength ratio about 4.64. A still leaner reduced candidate
reaches a 78.36 g proxy. None of these proxy masses is a sliced weight.

The actual one-wall 3D analysis gives **3.582 mm** front movement at the
planning modulus, leaving **1.418 mm** of the 5 mm total budget for rails,
mounts and other unmodeled movement. Proportional one-spool movement is 0.373 mm;
it does not qualify the whole rack or changed contact states.

Its raw maximum tensile stress is **47.417 MPa**, giving only **0.85** in the
conservative strength screen. The peak is near the lower fixing at
(3.163, 46.006, 7.113) mm, cell volume 0.00000736 mm³. Another peak near the
inner seat/core junction is approximately 46.65 MPa, with further peaks around
21 MPa at the window/seat. Total material above 10.125 MPa is 0.35024 mm³.
No finite peak was filtered out. This candidate needs local 3D redesign and
refinement before it can be considered feasible.

The structural CAD is one valid solid, 62,374.664 mm³ before sparse infill.
The dense modifier fails a tessellated-STL connectivity assertion after its
body-clipped tunnel saddle is added. That is a recorded export failure, not
an Orca crash. No complete light-candidate modifier 3MF or actual Orca mass is
published. [One-wall archive and failure status](studies/light-full-1w/README.md).

## Evidence and provenance

- [Baseline energy map](baseline-energy-map.png): the starting guide for window placement.
- Early sweeps: [initial](screening.json), [refinement](screening-refinement.json),
  [tuned](screening-tuned.json), [finalists](finalist-screening.json),
  [local reinforcement](local-tuning.json). These explored baseline stiffness.
- Current-limit screens: [16 candidates](constrained-screening.json) and
  [five finer frontier candidates](frontier-screening.json). A `screen_feasible`
  flag applies only to that reduced screen and is superseded by any failed 3D gate.
- [Selected reduced fields](studies/reduced-fields/) preserve the shaped,
  full-plane and light/frontier comparisons; other sweep outputs remain in
  their machine-readable ledgers. All five 3D fields are retained unfiltered.
- [Current source snapshot](exploration-sources/layout-constraint-screen.py.txt)
  and [earlier layout snapshot](exploration-sources/layout-baseline-match.py.txt)
  preserve the source stages. Candidate layout hashes include the source text
  and sorted parameter JSON; use the matching stage for historical reproduction.
- [Input layer outlines](inputs/e13-layer-outlines.json) retain the baseline
  STL hash and 120 layer polygons. [Checkpoint manifest](checkpoint-manifest.json)
  records hashes of the published Rev F evidence: exact binary/CAD bytes and
  LF-normalized UTF-8 for text, so Git line-ending conversion does not break it.

Two archived geometry JSON descriptions incorrectly hardcoded plane shape or
thickness while their parameters and geometry were correct. Their descriptions
are corrected with the original text retained in `checkpoint_metadata_correction`.
Numerical arrays, results, CAD and candidate parameters are unchanged.

## Reproduction

`python analysis/rev-f/audit_checkpoint.py` verifies source syntax, document
links, CAD/3MF/STL hashes, retained 3D peaks and equilibrium gates without
rerunning a solver. [Checkpoint verification](checkpoint-verification.json)
passes; it does not qualify the design.

Use the [pinned E13 engineering dependencies](../e13/requirements.txt). Run
CAD/native-library scripts through `run_native.py` if the local native stack
has interpreter-finalization crashes; exceptions and failing checks retain
nonzero exit status. The scripts use repository-relative inputs and write
regenerable intermediates into ignored `.work` directories.

```sh
python analysis/rev-f/run_native.py analysis/rev-f/build_analysis_geometry.py analysis/rev-f/full-plane-layout.json analysis/rev-f/.work/full-plane-4w
python analysis/rev-f/run_native.py analysis/rev-f/mesh_model.py print-material 4 2 1 --clean --directory analysis/rev-f/.work/full-plane-4w
python analysis/rev-f/run_native.py analysis/rev-f/solve3d.py print-material-4w-h2 --directory analysis/rev-f/.work/full-plane-4w
```

Use h1.5 and h1 for the finer four-wall fields. For the light candidate, use
`light-full-layout.json`, a separate output directory and one wall. The
three-wall shaped candidate uses `designs/rev-f/selected-layout.json` and the
analysis root by default. `constrained_screen.py` and `frontier_screen.py`
reproduce the latest reduced screens, not a genetic run. Current source
snapshots add inactive optional variables to older layouts; historical source
hashes can differ even where those defaults preserve geometry.

**Next:** implement the [seeded evolutionary optimizer](../../NEXT-SPRINT.md)
with cached evaluation, actual Orca mass and hard serviceability/3D/manufacturing
rejection gates. Buckling, physical fit, bonding, sustained/hot behavior and
long-term creep remain unqualified.
