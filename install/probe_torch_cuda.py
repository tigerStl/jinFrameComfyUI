"""Verify PyTorch was built with CUDA and can see GPU 0. Exit 1/2 on failure."""
import sys

try:
    import torch
except ImportError:
    sys.exit(3)

if not torch.cuda.is_available():
    sys.exit(1)
if not getattr(torch.version, "cuda", None):
    sys.exit(2)
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("device", torch.cuda.get_device_name(0))
sys.exit(0)
