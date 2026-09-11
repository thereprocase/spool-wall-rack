# Preserved F light candidate — modifier handoff repaired in G

The F one-wall full-plane candidate's helper export is repaired by extending
selection geometry through air instead of carving enclosed shells into it.
A Boolean comparison proves zero added/removed printed density material.
The body and mechanical design are unchanged.

It now slices successfully to **75.61 cm³ / 93.76 g** at 1.24 g/cm³ and passes
the current modifier/footprint checks. This replaces the old **87.81 g mass
estimate** with an actual Orca result. Its original F h2 tensile peak remains
47.42 MPa; no improved strength is claimed.

[Exact correction proof](helper-correction-verification.json) ·
[Toolpath audit](toolpath-verification.json) · [Parameters](selected-layout.json)
· [Quadratic buckling report](../../../../analysis/rev-g/BUCKLING.md)
· [Preserved original F field](../../../../analysis/rev-f/studies/light-full-1w/README.md).
