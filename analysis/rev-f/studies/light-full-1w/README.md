# Rev F light one-wall study — incomplete and constraint-failed

The [parameters](selected-layout.json) and [valid analysis geometry audit](geometry-1w.json)
are preserved with the [h2 results](print-material-1w-h2-results.json),
[mesh-quality audit](print-material-1w-h2-mesh-quality.json) and
[unfiltered field](print-material-1w-h2-solution.npz).

This is the 87.81 g **estimated**, unsliced candidate. At E = 1 GPa the front
moves 3.582 mm, leaving 1.418 mm of the total 5 mm budget for other contributors.
Its 47.417 MPa raw tensile peak gives a 0.85 scalar strength ratio, so it fails
the requested 4× screen. No material was removed to improve stress results.
[Full interpretation and extracted metrics](../../README.md).

The dense helper remains one valid STEP solid before tessellation, but its
STL export fails `repair_stl.py`'s connected-region assertion after adding the
body-clipped tunnel saddle. No complete modifier package or real sliced mass
exists for this candidate. Fixing that export is queued with the
[next sprint](../../../../NEXT-SPRINT.md); it does not resolve the strength failure.
