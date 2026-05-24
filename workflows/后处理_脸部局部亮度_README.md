# 后处理 · 脸部局部亮度

轻量 ComfyUI 工作流：**不加载扩散模型**，适合在 FLUX/SDXL 出图后微调脸部曝光。

## 文件

- `后处理_脸部局部亮度.json`

## 用法

1. 将肖像放入 `ComfyUI/input/`（或在节点里 Upload）。
2. 准备 **脸部蒙版** `face_mask.png`（与肖像同分辨率）：
   - **白色** = 要调整亮度的区域（脸、额头、鼻梁等）
   - **黑色** = 保持原图不变
3. 在 ComfyUI 中 **Load** 本 json，**Queue** 即可。
4. 输出目录：`output/post/face_brightness/`

## 主要参数

| 节点 | 建议 |
|------|------|
| **Adjust Brightness → factor** | `1.05`–`1.18` 提亮；`0.85`–`0.95` 压暗 |
| **Adjust Contrast → factor** | 保持 `1.0` 关闭；略增可用 `1.02`–`1.06` |
| **Grow Mask → expand** | `4`–`12`，略包住发际线与下颌 |
| **Feather Mask** | 四边 `24`–`48`，避免脸缘硬切 |

## 蒙版从哪里来

任选其一（无需本仓库额外节点）：

1. **Krita / Photoshop / Photopea**：软笔刷涂白脸部，导出 PNG。
2. **ComfyUI 蒙版编辑器**：在 `Load Image` 输出上右键 → 编辑蒙版（版本需支持 Mask Editor）。
3. **带 Alpha 的 PNG**：若原图透明底、脸不透明，可只用 `① 原图` 的 **MASK** 输出，删掉 `② 脸部蒙版` 分支，把 MASK 接到 `Grow Mask`（需自行改连线）。

## 节点说明

```
原图 ──┬──→ AdjustBrightness → AdjustContrast ──┐
       │                                         ├── Image Composite Masked → 保存
       └──→ destination ─────────────────────────┘
蒙版图 → ImageToMask → GrowMask → FeatherMask ──→ mask
```

- `Image Composite Masked`：**白蒙版区域**使用调亮/压暗后的整图，**黑区**保留原图。
- 下方 **蒙版预览** 用于检查羽化是否自然。

## 同步到 ComfyUI

```powershell
Copy-Item -Force "c:\tiger\videoModel\jinFrameComfyUI\workflows\后处理_脸部局部亮度.json" `
  "C:\ComfyUI\ComfyUI\user\default\workflows\"
```

## 与定妆/惊悚流程衔接

- FLUX 定妆：`Flux_I2I_定妆照参考.json` 出图 → 本工作流微调脸部高光。
- 近景肖像：`SDXL_AWPortraitXL_国人肖像.json` 同理。

若找不到 `AdjustBrightness` 节点，请更新 ComfyUI（该节点在 `dataset` 扩展中，随官方自带 extras 加载）。
