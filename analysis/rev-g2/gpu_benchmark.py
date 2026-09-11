"""Reproduce the installed, unmodified Warp mixed-elasticity example.

CPU/GPU agreement is a backend regression, not an independent physical solution.
The upstream problem is two-dimensional, nonlinear, and unrelated to G loads.
"""
from pathlib import Path
import argparse
import functools
import hashlib
import json
import threading
import time

import numpy as np
import warp as wp


class MemorySampler:
    """Sample device-wide VRAM; report allocator high water separately."""
    def __enter__(self):
        import pynvml as nv
        self.nv = nv
        nv.nvmlInit()
        self.handle = nv.nvmlDeviceGetHandleByIndex(0)
        self.values = [int(nv.nvmlDeviceGetMemoryInfo(self.handle).used)]
        self.stop = threading.Event()
        def sample():
            while not self.stop.wait(.02):
                self.values.append(int(nv.nvmlDeviceGetMemoryInfo(self.handle).used))
        self.thread = threading.Thread(target=sample, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()
        self.values.append(int(self.nv.nvmlDeviceGetMemoryInfo(self.handle).used))
        self.nv.nvmlShutdown()

    def report(self):
        return {"device_total_used_baseline_bytes": self.values[0],
                "device_total_used_sampled_peak_bytes": max(self.values),
                "sample_interval_seconds": .02, "samples": len(self.values),
                "scope": "Device-wide sampled memory includes display/other processes; not process-only VRAM."}


def run(device, repeats, displacement, poisson_ratio):
    from warp.examples.fem import example_mixed_elasticity as upstream
    values, runs = None, []
    with wp.ScopedDevice(device):
        for repeat in range(repeats):
            start = time.perf_counter()
            example = upstream.Example(quiet=True, resolution=25, degree=2,
                                       displacement=displacement, poisson_ratio=poisson_ratio, mesh="grid")
            wp.synchronize_device(device)
            created = time.perf_counter()
            example.step()
            wp.synchronize_device(device)
            finished = time.perf_counter()
            current = {"displacement": example._u_field.dof_values.numpy(),
                       "stress_coefficients": example._stress_field.dof_values.numpy()}
            assert all(np.isfinite(a).all() for a in current.values())
            if values is not None:
                for key in current:
                    np.testing.assert_allclose(current[key], values[key], rtol=2e-4, atol=2e-5)
            values = current
            runs.append({"repeat": repeat, "setup_seconds": created-start,
                         "step_seconds": finished-created, "total_seconds": finished-start})
    return values, runs, upstream


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path("analysis/rev-g2/gpu-validation/upstream"))
    ap.add_argument("--displacement", type=float, default=.1)
    ap.add_argument("--poisson-ratio", type=float, default=.5)
    ap.add_argument("--cg-tol", type=float, default=None,
                    help="Explicit upstream solver tolerance override; omit to reproduce upstream defaults.")
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    wp.init()
    assert wp.is_cuda_available(), "CUDA required; CPU fallback is forbidden for the GPU run"
    wp.set_module_options({"enable_backward": False})
    if args.cg_tol is not None:
        import warp.examples.fem.utils as utils
        utils.bsr_cg = functools.partial(utils.bsr_cg, tol=args.cg_tol)
    with MemorySampler() as memory:
        gpu, gpu_runs, upstream = run("cuda:0", 2, args.displacement, args.poisson_ratio)
    cpu, cpu_runs, _ = run("cpu", 1, args.displacement, args.poisson_ratio)
    comparison = {}
    for key in gpu:
        error = float(np.max(np.abs(gpu[key]-cpu[key])))
        relative = float(np.linalg.norm(gpu[key]-cpu[key])/np.linalg.norm(cpu[key]))
        comparison[key] = {"shape": list(gpu[key].shape), "max_abs_difference": error,
                           "relative_l2_difference": relative}
    np.savez_compressed(args.output.with_suffix(".npz"),
                        **{"gpu_"+k: v for k, v in gpu.items()},
                        **{"cpu_"+k: v for k, v in cpu.items()})
    passed = all(v['relative_l2_difference'] < 1e-4 for v in comparison.values())
    report = {"status": "PASS" if passed else "FAIL_BACKEND_AGREEMENT", "warp_version": wp.__version__,
              "device": wp.get_device("cuda:0").name,
              "upstream_module": "warp.examples.fem.example_mixed_elasticity",
              "upstream_source_sha256": hashlib.sha256(Path(upstream.__file__).read_bytes()).hexdigest(),
              "cg_tolerance_override": args.cg_tol,
              "backend_relative_l2_gate": 1e-4,
              "parameters": {"resolution": 25, "degree": 2, "displacement": args.displacement,
                             "poisson_ratio": args.poisson_ratio, "mesh": "grid"},
              "gpu_runs": gpu_runs, "cpu_runs": cpu_runs,
              "timing_note": "Wall times include synchronization. First calls include uncached JIT work; persistent caches may already be warm. CPU/GPU timings are not a controlled speedup comparison.",
              "memory": memory.report(),
              "warp_cuda_mempool_used_high_bytes": wp.get_mempool_used_mem_high("cuda:0"),
              "comparison": comparison,
              "scope": "Upstream 2D nonlinear example, CPU/GPU comparison; source unchanged, runtime CG tolerance override recorded explicitly. Not a 3D bracket or contact validation. Upstream stress coefficients are exported as produced, not interpreted as bracket stresses."}
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
