# Wan 2.2 标准图生视频 · 糊 / 重影

## 两个工作流

| 文件 | 用途 |
|------|------|
| `I2V_标准_图生视频.json` | 日常：768×432、49 帧、LoRA **0.65**、稳态向 prompt |
| `I2V_标准_图生视频_稳态少虚影.json` | 重影仍重：LoRA **0.6**、更严 prompt |

## 为什么会糊？

- **GGUF Q3_K_S** 量化低，细节软（可换 **Q4_K_S** / Q4_K_M，显存更高）
- **Lightning 4-step LoRA** 步数少，偏快偏软
- 分辨率与首帧**比例不一致**会被拉伸变糊

## 为什么会重影？

- **length 65+**、prompt 写 **turn / walk / spin / camera pan**
- **LoRA strength 1.0** 过猛（模板已改为 0.65 / 0.6）
- 8GB 上 Wan 不适合「一张图里大转身」→ 用分镜关键帧 + 短片段（见 `wan视频流/`）

## 手动微调（子图内）

1. **length** → `49`
2. **width×height** → `768×432` 或与首帧同比例
3. **LoRA strength** → `0.55`–`0.7`
4. **Prompt** → 只写呼吸、眨眼、极微动

## 重建 json

```powershell
python c:\tiger\videoModel\jinFrameComfyUI\install\patch_i2v_anti_ghost.py
```
