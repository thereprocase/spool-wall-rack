# Project instructions

- Read [the current handoff](RESTART-2026-09-11.md) and [G2 requirements](G2-BRIEF.md) before work. They supersede [archived revision instructions](docs/archive/AGENTS-2026-09-11.md).
- Next: establish a free, tested GPU analysis route for the actual sliced material. Do not restart the stopped whole-part CPU meshing jobs. G2 architecture CAD remains unfinished.
- Preserve E13, F and G evidence, existing work, raw failures and caches. Keep geometry, slicing, numerical analysis and physical qualification claims distinct; retain every finite stress cell and raw peak.
- Use OrcaSlicer: P1S, 0.4 mm nozzle, PETG/ASA, at least two walls, 0% base infill and 100% helper regions. Sacrificial 0.4 mm bridges count as spent plastic but receive zero structural or bond credit.
- Checkpoint each implemented idea with aligned body/helper STEP files, notes and verification. Update [the download index](PRINT-CANDIDATES.md), README and DESIGN-JOURNAL; clearly label unbuilt or unqualified candidates. Commit and publish meaningful checkpoints.
- Keep personal information, credentials, conversation transcripts and absolute local paths out of commits. Use the generic Rack Engineering commit identity.
