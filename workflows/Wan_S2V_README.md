# Wan 2.2 S2V（WanSoundImageToVideo）有声图生视频

与 **`Wan22_I2V_GGUF_8GB`**（无声、GGUF）是**另一套模型**。

## 工作流

| 文件 | 说明 |
|------|------|
| `Wan22_S2V_有声图生视频_简版.json` | 单次 ~77 帧，适合试跑 |
| `Wan22_S2V_有声图生视频_官方完整.json` | 官方长音频 + 多段 Extend |

ComfyUI 路径：`user/default/workflows/`

## 安装模型

```powershell
C:\ComfyUI\install\install_wan22_s2v.ps1
```

## 模型目录

| 文件 | 目录 |
|------|------|
| `wan2.2_s2v_14B_fp8_scaled.safetensors` | `models/diffusion_models/` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `models/text_encoders/` |
| `wan_2.1_vae.safetensors` | `models/vae/` |
| `wav2vec2_large_english_fp16.safetensors` | `models/audio_encoders/` |
| `wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` | `models/loras/`（可选加速） |

## 节点链路（简版）

```
LoadAudio + AudioEncoder → WanSoundImageToVideo ← LoadImage（参考脸）
                              ↓
                         KSampler → VAEDecode → CreateVideo(+原音频) → SaveVideo
```

## 时长

- **length** = 帧数（简版默认 **77**）
- **fps** = **16**（CreateVideo）
- 约 **77÷16 ≈ 4.8 秒** 一段  
- 更长：用官方完整版，按音频秒数增加 **WanSoundImageToVideoExtend** 段数

## 显存

建议 **16GB+**。RTX 5060 8GB 可能 OOM（14B 模型，非 GGUF）。

官方文档：https://docs.comfy.org/tutorials/video/wan/wan2-2-s2v
