# HunyuanDiT 图形合成（已拆分）

| 文件 | 用途 | Queue |
|------|------|-------|
| `HunyuanDiT_图形合成_01_文生图.json` | 纯中文分层文生图 | **只开这个** |
| `HunyuanDiT_图形合成_02_图生图.json` | 参考图换背景/融氛围 | **只开这个** |
| `HunyuanDiT_图形合成.json` | 旧合并版（不推荐一次 Queue） | 勿用 |

## ② 图生图链路

`LoadImage` → `VAEEncode` → `KSampler` → `VAEDecode` → `SaveImage`

## 模型

`hunyuan_dit_comfyui/hunyuan_dit_1.2.safetensors` — `install/install_hunyuan_dit.ps1`

## 8GB

`--lowvram --cpu-vae`，单流程约 5~12 分钟。

## 重建

```powershell
python install/build_hunyuan_compose_split.py
```
