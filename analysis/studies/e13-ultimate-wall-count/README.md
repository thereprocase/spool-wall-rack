# E13 wall count versus short-term tensile strength

This study records the requested counterfactual: retain E13 geometry and all
four 1.2 mm solid plates, ignore serviceability and creep, and screen lower
wall counts against a strength/stress ratio of four. It does **not** change
the released E13 print settings or establish a minimum safe wall count.

The layer-integrated plane-stress model uses the actual finished STL, the
12 kg equivalent load per bracket, compression-only wall contact, projected
fastener restraints, and zero sparse-infill credit. The nominal planar mesh
size is 1 mm. The 2/3/4/6-wall fields were newly solved; 8/10-wall fields are
the preserved E13 comparisons. Every run passes the solver's independent
free-residual, force and moment checks.

| Walls | Ideal contour thickness (mm) | Peak tensile stress (MPa) | PLA UTS / peak | PETG UTS / peak |
|---:|---:|---:|---:|---:|
| 2 | 0.827 | 7.749 | 6.75 | 6.19 |
| 3 | 1.234 | 6.384 | 8.19 | 7.51 |
| 4 | 1.641 | 5.603 | 9.34 | 8.56 |
| 6 | 2.455 | 5.239 | 9.98 | 9.16 |
| 8 | 3.270 | 4.608 | 11.35 | 10.41 |
| 10 | 4.084 | 4.805 | 10.88 | 9.98 |

The ratios use the project's reference printed XY tensile strengths:
[PolyLite PLA, 52.3 MPa](https://polymaker.com/wp-content/uploads/lana-downloads/PolyLite-PLA_TDS_EN_V5.4.pdf)
and [Polymaker PETG, 47.96 MPa](https://polymaker.com/wp-content/uploads/Polymaker-PETG_TDS_EN_V1.0.pdf).
They are typical coupon properties, not measured properties of a particular rack.

Even two walls clears four in this **reduced in-plane screen**. Four walls
was identified as a candidate for further investigation. The model cannot
resolve through-width wall/plate intersections, full screw contact, print
orthotropy, local buckling or snap insertion. E13's full 3D fields retain
mesh-sensitive local peaks above the corresponding strength/4 limits.
Consequently these ratios are not demonstrated full-bracket factors of safety.

This motivates Rev F's different question: can material be moved into more
effective regions to reduce actual sliced weight while retaining stiffness?
Simply reducing walls increases movement; the four continuous plates remain
substantial structural material in every row above.

[Machine-readable values](screen.json) · [E13 3D hotspot audit](../../e13/HOTSPOTS.md)

Run `python run.py` to reproduce. New fields are stored here; reference 8/10-wall
fields remain in `analysis/e13`. All are based on the published E13 geometry.
