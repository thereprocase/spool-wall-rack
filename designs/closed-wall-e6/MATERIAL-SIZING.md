# How much additional section for PLA or PETG?

**Proposed shared starting point: 3.6 mm modeled structural perimeters and a 34 mm-deep straight arm, retaining the four continuous 1.2 mm plates and 24 mm overall width.** Carry the added section smoothly through the knee; do not strengthen only the midpoint. E6 CAD remains unchanged pending this study's implementation and local verification.

The present straight arm is approximately 28 mm deep with 2.4 mm structural perimeters. An ideal rectangular multi-cell section gives the following comparison. All modeled solid counts; infill counts zero.

| Study | Straight-arm plastic increase | Geometric bending stiffness, I | Pure bending stress reduction at equal moment |
|---|---:|---:|---:|
| 3.6 mm perimeter only; 28 mm depth | 20% | 1.23× | 19% |
| One more 1.2 mm continuous plate; 24.4 mm width; original depth/perimeter | 13% | 1.07× | 6% |
| 3.6 mm perimeter; 32 mm depth | 29% | 1.72× | 34% |
| **3.6 mm perimeter; 34 mm depth** | **33%** | **2.00×** | **39%** |
| 3.6 mm perimeter; 36 mm depth | 37% | 2.30× | 44% |

These are local section ratios, not whole-part mass increases, whole-bracket deflections or reductions in the previously reported maximum combined stress. The rectangular baseline has I = 23,925 mm⁴ versus 22,261 mm⁴ at the finished CAD midpoint, illustrating the approximation. Chamfers and their cavity-rim reinforcement, the irregular knee, sleeves, snap roots, shear and plate stability require final-CAD checks.

For width b, depth h, perimeter thickness t and n continuous plates of thickness p, the model subtracts the air bands from the outer rectangle:

`A = b*h - (b - n*p)*(h - 2*t)`

`I = [b*h^3 - (b - n*p)*(h - 2*t)^3]/12; S = 2*I/h`

The perimeter increase is particularly useful in the upper and lower longitudinal portions of the arm, where material lies farthest from its bending neutral axis. Additional full-depth plates also carry in-plane bending and shear, but adding one alone gives less bending benefit per added material in this section. Their number should also reflect stability and manufacturing requirements.

## Material interpretation

Using the specific reference flexural moduli in the [material assessment](MATERIAL-CASES.md), PETG needs approximately **41% more I** to match the original ASA section's initial bending stiffness. The older PolyLite PETG reference would need 69% more. The 34 mm candidate provides about 100% more I, producing approximately **1.42× the original ASA initial EI** with the current PETG reference, or 1.18× with the legacy PETG reference. These comparisons use typical reference properties, not properties measured at 85°F or after creep. [Current PETG source](https://cdn.shopify.com/s/files/1/0548/7299/7945/files/PETG_TDS_Polymaker_297e875c-5d38-4d2b-ba68-eef8916de183.pdf?v=1761581533).

The PLA reference already has approximately the same initial bending modulus as ASA, so no extra section is required merely to match that initial stiffness. The proposed increase lowers working stress and provides deformation margin for either material; it does not establish how much is required for long-term creep. Published PLA research shows that creep can continue well below Tg, but does not supply a transferable factor for this grade and temperature envelope. [PLA creep research](https://arxiv.org/abs/2302.11240).

For a linear creep-stiffness sensitivity, doubling I offsets a halving of effective modulus when comparing otherwise identical beam geometry and loading. **A 50% retained modulus is an illustrative assumption, not a measured PLA/PETG retention value or a prediction of service life.** Geometry cannot be sized to a specific life until a defensible time/temperature-dependent material basis exists.

## Implementation intent

Add the 6 mm below the arm to preserve spool clearance and rail positions. Expect approximately 6 mm additional extension below the spool, about 39 mm total for the 200 mm reference spool, subject to final geometry. Continue the lower load path into the full-contact wall leg, maintain smooth knee transitions, and recheck the critical sections. Preserve thin working snap fingers and their smooth roots; do not scale the complete retainer by the perimeter increase.

The four plates stay at 1.2 mm to retain the solid-layer strategy. The thicker modeled perimeter needs matching sliced solid paths rather than the original three-wall assumption. Empty-cavity roof printing remains unresolved and must be handled before representative mechanical testing. The 12 kg sustained/hot qualification target remains unchanged; this sizing study does not release a safe spool count.

[Calculation script](size_material_alternatives.py) · [Computed values](material-sizing.json).
