"""Patch ComfyUI_LTX2_SM for RTX 50 / sm_120: disable broken xformers, force PyTorch SDPA.

Typical error on RTX 5060:
  NotImplementedError: No operator found for `memory_efficient_attention_forward`
  requires device with capability <= (9, 0) but your GPU has capability (12, 0)

Run after ComfyUI_LTX2_SM install/update:
  python install/patch_ltx2_sm_pytorch_attention.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import COMFY_ROOT  # noqa: E402

IMPORT_BLOCK_OLD = """memory_efficient_attention = None
flash_attn_interface = None
try:
    from xformers.ops import memory_efficient_attention
except ImportError:
    memory_efficient_attention = None"""

IMPORT_BLOCK_NEW = """memory_efficient_attention = None
flash_attn_interface = None
try:
    from xformers.ops import memory_efficient_attention as _xformers_mea
    memory_efficient_attention = _xformers_mea
    # xformers fa2/fa3/cutlass only support CC <= 9.0 (RTX 40 and older)
    if torch.cuda.is_available():
        _major, _minor = torch.cuda.get_device_capability(0)
        if _major >= 10:
            memory_efficient_attention = None
except ImportError:
    memory_efficient_attention = None"""

DEFAULT_OLD = """        else:
            # Default behavior: XFormers if installed else - PyTorch
            return XFormersAttention() if memory_efficient_attention is not None else PytorchAttention()"""

DEFAULT_NEW = """        else:
            return PytorchAttention()"""

XFORMERS_CALL_OLD = """            out = memory_efficient_attention(q.to(v.dtype), k.to(v.dtype), v, attn_bias=mask, p=0.0)
        out = out.reshape(b, -1, heads * dim_head)
        return out"""


XFORMERS_CALL_NEW = """            try:
                out = memory_efficient_attention(q.to(v.dtype), k.to(v.dtype), v, attn_bias=mask, p=0.0)
            except NotImplementedError:
                return PytorchAttention()(q, k, v, heads, mask)
        else:
            try:
                out = memory_efficient_attention(q.to(v.dtype), k.to(v.dtype), v, attn_bias=None, p=0.0)
            except NotImplementedError:
                return PytorchAttention()(q, k, v, heads, mask)
        out = out.reshape(b, -1, heads * dim_head)
        return out"""

CONNECTOR_IMPORT_OLD = "from ...model.transformer.attention import Attention"
CONNECTOR_IMPORT_NEW = "from ...model.transformer.attention import Attention, AttentionFunction"

CONNECTOR_ATTN_OLD = """        self.attn1 = Attention(
            query_dim=dim,
            heads=heads,
            dim_head=dim_head,
            rope_type=rope_type,
            apply_gated_attention=apply_gated_attention,
        )"""

CONNECTOR_ATTN_NEW = """        self.attn1 = Attention(
            query_dim=dim,
            heads=heads,
            dim_head=dim_head,
            rope_type=rope_type,
            apply_gated_attention=apply_gated_attention,
            attention_function=AttentionFunction.PYTORCH,
        )"""


def _apply(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise ValueError(f"{label}: expected block not found")
    return text.replace(old, new, 1)


def patch_attention(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = _apply(text, IMPORT_BLOCK_OLD, IMPORT_BLOCK_NEW, "import block")
    # partial prior patch
    partial = """        else:
            # Default: PyTorch SDPA (xformers often lacks kernels on RTX 50 / new arch -> NotImplementedError)
            import os
            if os.environ.get("LTX2_USE_XFORMERS", "").lower() in ("1", "true", "yes"):
                if memory_efficient_attention is not None:
                    return XFormersAttention()
            return PytorchAttention()"""
    if partial in text:
        text = text.replace(partial, DEFAULT_NEW, 1)
    else:
        text = _apply(text, DEFAULT_OLD, DEFAULT_NEW, "DEFAULT branch")
    if XFORMERS_CALL_NEW not in text:
        text = _apply(text, XFORMERS_CALL_OLD, XFORMERS_CALL_NEW, "XFormersAttention")
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def patch_connector(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if CONNECTOR_ATTN_NEW not in text:
        if CONNECTOR_IMPORT_NEW not in text:
            text = _apply(text, CONNECTOR_IMPORT_OLD, CONNECTOR_IMPORT_NEW, "connector import")
        text = _apply(text, CONNECTOR_ATTN_OLD, CONNECTOR_ATTN_NEW, "connector Attention")
        path.write_text(text, encoding="utf-8")
        print("patched", path)
    else:
        print("already patched", path)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ComfyRoot", default=str(COMFY_ROOT))
    args = p.parse_args()
    root = Path(args.ComfyRoot) / "custom_nodes" / "ComfyUI_LTX2_SM" / "LTX2" / "ltx_core"
    patch_attention(root / "model" / "transformer" / "attention.py")
    patch_connector(root / "text_encoders" / "gemma" / "embeddings_connector.py")
    print("Done. Fully quit ComfyUI and start again (run_sulphur.bat).")


if __name__ == "__main__":
    main()
