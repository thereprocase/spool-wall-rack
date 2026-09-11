# Recovered print evidence

The successful overnight ASA archive is associated with **E13**, not an established eight-wall G print. Its filename and closed-face preview agree with the downloaded STEP, which matches the published E13 assembly byte for byte. The newer downloaded STEP matches G byte for byte.

| Evidence | Polymer | Walls | Base infill | Minimum top/bottom thickness | Confidence |
|---|---|---:|---:|---:|---|
| Overnight completed archive, two E13-associated brackets | PolyLite ASA | 7 | 10% | 1.6 mm | Actual stored slice and completed-job filename recovered |
| Saved project using G and three 100% helpers | PolyLite PETG | 2 | 10% | 1.6 mm | Saved during the morning print; not proof of its exact submitted slice |
| Later G-named archive currently on the printer | PLA profile | 5 | 20% | 1.6 mm | Newer reused filename; not the earlier PETG submission |

Both recovered process configurations also store five top and three bottom layers at 0.2 mm, alongside the 1.6 mm minimum thickness settings. Do not interpret the layer counts alone as 1.0/0.6 mm skins.

The ASA archive estimates 256.94 g for two objects together. That is a slicer estimate, not measured mass. The saved PETG project retains all three expected G helpers as 100% infill modifiers. The sliced-only ASA archive omits source meshes and per-part modifier configuration; its exact helper setup is not recovered from that archive.

The original PETG submitted archive was not recovered. The cached G-code's first 65,536 bytes and total size match the newer PLA archive; the cache does not preserve the earlier PETG settings. The printer's filename has been reused, and the saved project was written after the completed morning job began. Bridge history records the completed jobs but does not retain their old project contents. Filament profile labels establish intended slicing material, not independent chemical identification of the loaded filament.

These findings prevent assigning the observed flexibility change solely to ASA versus PETG. Geometry and wall count changed as well. The eight-wall G schedules in this folder remain deliberate virtual controls, not reconstructions of the successful physical print. Their savings retain that explicit denominator.

The compact JSON receipt includes source hashes, selected settings and the exact public STEP matches. Original printer archives and private job metadata remain local and are excluded from Git.

https://github.com/thereprocase/spool-wall-rack/blob/main/designs/rev-g2/print-controls/recovered-print-evidence.json
