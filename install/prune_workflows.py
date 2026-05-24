"""Keep one canonical workflow per model+process; move the rest to workflowbackup."""
from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_ROOT  # noqa: E402

WF = REPO_ROOT / "workflows"
BACKUP_ROOT = Path(r"c:\tiger\videoModels\workflowbackup") / "jinFrameComfyUI"

# Relative paths under workflows/ to KEEP (JSON + essential docs)
KEEP: set[str] = {
    "工作流目录说明.md",
    "I2V_Wan_README.md",
    "Wan_S2V_README.md",
    "后处理_脸部局部亮度_README.md",
    "HunyuanDiT_图形合成_README.md",
    "Flux_Sample_T2I.json",
    "Flux_T2I_风格_清冷高级.json",
    "Flux_I2I_定妆照参考.json",
    "FLUX_人像写实化_I2I.json",
    "SDXL_AWPortraitXL_国人肖像.json",
    "HunyuanDiT_T2I_中国风格.json",
    "HunyuanDiT_图形合成_02_图生图.json",
    "Kolors_T2I_惊悚_场景.json",
    "Flux_T2I_惊悚_大厅走廊.json",
    "Flux_人物场景融合_单人.json",
    "I2V_标准_图生视频_稳态少虚影.json",
    "Wan22_S2V_有声图生视频_简版.json",
    "ltx23_i2v distilled.json",
    "ltx23_t2v distilled.json",
    "LTX_Template_首帧.json",
    "后处理_脸部局部亮度.json",
    "ltx云GPU/README.md",
    "ltx云GPU/LTX23_云GPU_I2V_distilled_fp8.json",
    "ltx云GPU/LTX23_云GPU_T2V_distilled_fp8.json",
    "ltx视频流/00_分镜流程说明.md",
    "ltx视频流/02_LTX_片段_A_首尾_kf01到kf02.json",
    "wan视频流/00_分镜流程说明.md",
    "wan视频流/02_Wan_片段_A_kf01到kf02.json",
}

# Promote these sources into KEEP paths before pruning
PROMOTE: list[tuple[str, str]] = [
    ("人像写实化/01_FLUX_人像写实化_I2I.json", "FLUX_人像写实化_I2I.json"),
    ("Kolors_日系惊悚/Kolors_T2I_惊悚_场景.json", "Kolors_T2I_惊悚_场景.json"),
    ("日系惊悚_场景/Flux_T2I_惊悚_大厅走廊.json", "Flux_T2I_惊悚_大厅走廊.json"),
    ("日系惊悚_人物场景融合/Flux_人物场景融合_单人.json", "Flux_人物场景融合_单人.json"),
]


def _promote() -> None:
    for src_rel, dst_rel in PROMOTE:
        src = WF / src_rel
        dst = WF / dst_rel
        if src.is_file() and not dst.exists():
            dst.write_bytes(src.read_bytes())
            print(f"promoted: {dst_rel}")


def _prune(dry_run: bool = False) -> tuple[int, int]:
    moved = 0
    kept = 0
    for path in sorted(WF.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(WF).as_posix()
        if rel in KEEP:
            kept += 1
            continue
        dest = BACKUP_ROOT / rel
        if dry_run:
            print(f"would move: {rel}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest.unlink()
            shutil.move(str(path), str(dest))
            print(f"moved: {rel}")
        moved += 1
    if not dry_run:
        for d in sorted(WF.rglob("*"), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
    return moved, kept


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    (BACKUP_ROOT / "_ARCHIVED.txt").write_text(
        f"Archived from jinFrameComfyUI on {date.today().isoformat()}\n",
        encoding="utf-8",
    )
    _promote()
    moved, kept = _prune(dry_run=args.dry_run)
    print(f"done: kept {kept}, moved {moved} -> {BACKUP_ROOT}")


if __name__ == "__main__":
    main()
