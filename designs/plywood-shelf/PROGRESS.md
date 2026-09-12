# Closet shelf — progress and restart handoff

Status as of 2026-09-12: **V3 CAD is published; the latest molding/retainer requirements are not yet built or verified. V4 source is a preliminary, unexecuted checkpoint.**

## Latest design requirements

- Install the shelf above the closet.
- Keep mirrored left/right triangular bracket bodies above the plywood.
- Use two brackets, each with three fasteners into a stud.
- Use a continuous, approximately 14-inch-deep plywood shelf.
- Put the plywood rear edge against the wall and bearing on the top of the molding.
- The molding projects 3/4 inch (19.05 mm); clear a full 1 inch (25.4 mm) from the wall.
- Brackets must step over that molding envelope before extending below the plywood.
- Plywood should install with a drop-and-flop motion into bracket retainers.

The supplied **Closet.zip contains a 3D closet model, not photographs**. It has not been unpacked or inspected. No measurements, units, trim profile or ceiling clearances have been recovered from it.

## Published checkpoint: V3

[Source, STEP/STL, drawings and renders](README.md) remain the last executed geometry checkpoint. The `above-shelf-v3-wall-flush` receipt verifies connected mirrored solids, plywood clearance, zero rear wall gap, underside bearing on the ledges, driver access, pilot backing and nominal bed/brim fit.

V3 uses a 355.6 mm board depth and 260 mm bracket projection, giving 95.6 mm front overhang. Its example uses 19.05 mm plywood and 812.8 mm stud spacing, producing a 779.8 mm board length. These thickness/span assumptions have not been confirmed from the closet model.

**V3 does not clear the molding:** its lower ledge continues to the wall. It also lacks the new rear hold-down retainers. Do not treat its images or exports as satisfying the latest request.

V3 has not been sliced or physically tested. Its solid CAD volume is 760.94 cm3 per bracket; that is not measured printed mass. No structural capacity or load rating is established.

## Preliminary V4 source preserved

- [Draft CadQuery builder](v4-draft/build.py)
- [Draft parameters](v4-draft/parameters.json)
- [Draft status and execution notes](v4-draft/README.md)

This source has **not run**. No V4 STEP/STL/helper exports, actual renders, successful tests, or motion-clearance results exist.

The draft proposes a 25.4 mm horizontal molding clearance and 1 mm vertical relief. The ledge starts beyond that clearance, leaving the plywood rear edge to bear on the molding. Small rear tabs extend over the plywood; the proposed sequence slides the tilted board under those tabs, then lowers the front onto the ledges.

The planned checks include molding clearance, rear bearing, a 15-degree-to-flat installation sweep, a 25 mm approach slide, and a rear-tab clearance calculation. Those are proposed checks in unexecuted source, not completed validation. The draft retains optional pilot holes; the proposed normal installation does not require screws through the plywood.

The tabs are a tentative interpretation of the requested retainers. They limit rear uplift when seated but do not lock the board against deliberate forward withdrawal. Confirm the intended capture/release behavior before treating this as a finished retention mechanism.

## Assumptions still requiring review

| Parameter | Draft value | Basis |
|---|---:|---|
| Molding projection | 19.05 mm | Supplied requirement |
| Horizontal molding clearance | 25.4 mm | Supplied requirement |
| Vertical relief above molding | 1 mm | Draft choice |
| Plywood thickness | 19.05 mm | Existing assumption; measure actual board |
| Stud spacing | 812.8 mm | Existing 32-inch example; not established |
| Molding height in context geometry | 60 mm | Illustration only; not a measurement |
| Rear tab fore-aft reach / inward overlap | 6 / 8 mm | Tentative geometry |
| Rear tab thickness / top clearance | 6 / 1.5 mm | Tentative geometry |
| Installation tilt / approach slide | 15 degrees / 25 mm | Proposed sequence; not tested |

Molding intentionally carries a rear shelf reaction under the latest requirement. Its actual top bearing surface, attachment and capacity remain unverified. The bracket step, ledge root and retainer roots introduce additional local and layer-bond demands. Preserve these unresolved questions when resuming.

## Why work paused

The interactive file-execution environment failed to start. No callable local shell/archive extractor was available. The native file reader recognized the archive as application/zip but returned no readable content. The model itself remains unread.

Prior CAD execution used the repository's GitHub Actions build. That does not establish access to the privately supplied closet archive. The archive and any private transfer links have not been committed to this public repository.

## Resume in this order

1. Unpack Closet.zip in a functioning file-execution environment. Identify the actual model format and inspect geometry, units/scale, orientation and any texture files.
2. Identify the molding top, wall plane, projection, profile and available space above the closet. Record measured quantities separately from model estimates and assumptions. Establish actual stud locations separately.
3. Confirm plywood dimensions and the intended retainer engagement/release sequence.
4. Review the preliminary V4 source against that model; revise the clearance notch, ledges and tabs before promoting it into the active build.
5. Build connected bodies and aligned helpers, verify installation motion and clearances, and update the actual CAD renders and receipt.
6. Slice for the P1S and inspect exclusions, toolpaths, bonding, mass and print time. Assess the load path, molding support and sustained loading before release.

Keep current V3 exports and prior evidence identifiable. Do not mix draft V4 source with V3 verification or label V3 renders as V4.
