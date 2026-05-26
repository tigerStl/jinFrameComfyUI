"""Verify PyTorch CUDA for this machine's profile (cu130 vs cu128 nightly)."""
import json
import os
import sys
from pathlib import Path

try:
    import torch
except ImportError:
    sys.exit(3)


def _read_expected_min_major() -> int:
    env = os.environ.get("JINFRAME_MIN_CUDA_MAJOR", "").strip()
    if env.isdigit():
        return int(env)
    repo = os.environ.get("JINFRAME_REPO_ROOT", "").strip()
    if repo:
        p = Path(repo) / "jinframe_gpu_profile.json"
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                m = data.get("min_cuda_major")
                if m is not None:
                    return int(m)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
    return 13


def _cuda_build_major() -> int:
    v = getattr(torch.version, "cuda", None) or ""
    try:
        return int(str(v).split(".")[0])
    except (ValueError, IndexError):
        return 0


min_major = _read_expected_min_major()

if not torch.cuda.is_available():
    print("torch.cuda.is_available() is False")
    sys.exit(1)

cuda_ver = getattr(torch.version, "cuda", None)
if not cuda_ver:
    print("torch built without CUDA")
    sys.exit(2)

major = _cuda_build_major()
if major < min_major:
    print(
        "torch",
        torch.__version__,
        "cuda",
        cuda_ver,
        f"- need CUDA>={min_major}.0 for this GPU profile",
    )
    sys.exit(4)

try:
    _ = torch.cuda.device_count()
    name = torch.cuda.get_device_name(0)
except Exception as exc:
    print("cuda init failed:", exc)
    sys.exit(5)

print("torch", torch.__version__, "cuda", cuda_ver)
print("device", name)
sys.exit(0)
