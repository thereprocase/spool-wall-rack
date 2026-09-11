# Retained unsuccessful GPU checks

- `default-tolerance/upstream.json` and `.npz`: the default upstream material
  and load missed the original `1e-4` CPU/GPU stress comparison gate. The parent
  directory's `upstream.json` and `.npz` are the same original output pair.
- `near-incompressible.json` and `.npz`: the severe upstream CLI-default case
  also missed that gate. This reproduces the initial failed comparison with
  full field export. The initial failure message was
  `AssertionError: ('stress_coefficients', 0.0005125424358993769)`.
- `fixture-count/hex-fixtures.json`: incomplete first 3D fixture suite, stopped
  by the hand-written assertion `len(cells) == 320`. The correct count is
  `10 * (8*6 - 4*2) = 400`. Its affine and hollow-bending fields are preserved
  in the same directory. This was a fixture arithmetic error; the independent
  displacement comparison had passed before the assertion.

Raw local execution logs are retained under
`analysis/rev-g2/.work/gpu-route/logs`. They contain local runtime paths and are
not redistributed. The accepted numerical results are identified explicitly in
[the GPU checkpoint](../../GPU-VALIDATION.md). No stress cell or raw peak from
these exported attempts has been trimmed or substituted by a percentile.
