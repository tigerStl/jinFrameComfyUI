<p align="center">
  <img src="jinZhenLogo.png" alt="Golden Frame AI Video Platform" width="280" />
</p>

# Golden Frame AI Video Platform · ComfyUI

**Golden Frame AI Video Platform** is an **image + video** production stack for ComfyUI: ready-to-run standard workflows, one-click model downloads, workflow sync and safety tooling, and the built-in **JinFrame Assistant** panel so you can download models, open workflows, and edit flows from chat without living in PowerShell.

> Model weights (`.safetensors` / `.gguf`) are large and downloaded separately. Versions are pinned for each workflow — see **[MODELS.md](MODELS.md)** for install and verification.

**中文文档：** [README.md](README.md)

---

## What the platform does

> Per-workflow purpose, parameters, and pipelines: **[Preset workflows (detailed)](#preset-workflows-detailed)** below.

### Image (still frames / look dev / compositing)

| Capability | Description | Example workflow |
|------------|-------------|------------------|
| **T2I** | Text-to-image; sample and style templates | `Flux_Sample_T2I.json`, `Flux_T2I_风格_清冷高级.json` |
| **I2I** | Reference-based retouch, background swap, photoreal polish | `Flux_I2I_定妆照参考.json`, `FLUX_人像写实化_I2I.json` |
| **Character + scene** | Keep identity, place subject in horror corridor / stairs, etc. | `Flux_人物场景融合_单人.json` |
| **East Asian portrait** | SDXL + AWPortrait XL | `SDXL_AWPortraitXL_国人肖像.json` |
| **Chinese aesthetic T2I** | Hunyuan DiT, layered Chinese prompts | `HunyuanDiT_T2I_中国风格.json` |
| **Graphic composite I2I** | Reference + layered Chinese prompt composite | `HunyuanDiT_图形合成_02_图生图.json` |
| **Kolors Chinese scenes** | Kwai Kolors stack | `Kolors_T2I_惊悚_场景.json` |
| **Horror scene T2I** | FLUX liminal corridors / halls | `Flux_T2I_惊悚_大厅走廊.json` |

### Video (I2V / T2V / audio-driven)

| Capability | Description | Example workflow |
|------------|-------------|------------------|
| **Wan 2.2 I2V** | GGUF for **~8GB VRAM**; anti-ghost tuning | `I2V_标准_图生视频_稳态少虚影.json` |
| **Wan 2.2 S2V** | Image + audio lip-sync / rhythm (short) | `Wan22_S2V_有声图生视频_简版.json` |
| **LTX 2.3 local** | High-quality I2V/T2V + distill LoRA | `ltx23_i2v distilled.json`, `ltx23_t2v distilled.json` |
| **LTX 2.3 cloud GPU** | fp8 weights, **24GB+ VRAM** | `workflows/ltx云GPU/LTX23_云GPU_*` |
| **LTX frame templates** | Lock first / last / start frame | `LTX_Template_首帧.json`, etc. |

### Storyboard & longer edits (recommended on 8GB)

For **8GB VRAM**, avoid complex camera moves in a single long clip:

1. **Look dev / keyframes** — FLUX or SDXL → `kf_01`, `kf_02`, … stills  
2. **Short segments** — Wan or LTX between adjacent keyframes  
3. **Concat** — ffmpeg or scripts in `wan视频流/` / `ltx视频流/`

- `workflows/wan视频流/` — Wan segments + `00_分镜流程说明.md`  
- `workflows/ltx视频流/` — LTX segments + `00_分镜流程说明.md`  

### Post-processing

| Capability | Description |
|------------|-------------|
| **Face local brightness** | Tune face exposure/contrast on stills or clips | `后处理_脸部局部亮度.json` |

### Workflow governance

| Feature | Role |
|---------|------|
| **Canonical set** | One JSON per model × pipeline |
| **Sync to ComfyUI** | Copy `workflows/` to ComfyUI sidebar |
| **Prompt sanitize** | Replace unsafe **positive** prompts; keep negative `nsfw` blocks |
| **Prune** | Move non-standard JSON to local backup (not in Git) |

---

## JinFrame Assistant (ComfyUI panel)

For users who prefer the UI over scripts. After install, use the blue **💬** button on the **right** of ComfyUI.

```powershell
.\install\install_jinframe_assistant.ps1
# Fully quit and restart ComfyUI after install
```

| Area | Function |
|------|----------|
| **Model packs** | FLUX / SDXL / Hunyuan / Kolors / Wan / LTX groups; **one-click download** into `models\` |
| **Download status** | Local file presence and size checks |
| **Cursor Agent** | With API key + `JINFRAME_REPO_ROOT`, chat can edit `workflows/` in this repo |
| **Local chat** | Ollama + Qwen for usage help (`ollama pull qwen2.5:7b`) |
| **Config** | Stored in `ComfyUI\user\default\jinframe_assistant_config.json` (not in Git) |

Model packs match standard workflows — see `comfyui_extension/ComfyUI_JinFrameAssistant/models_manifest.json`.

---

## Quick start (recommended order)

### 0. One-click install (Windows, beginners)

At the **repo root**, double-click:

```text
一键安装.bat
```

Or run `allInOneInstall\一键安装.exe` (or `AllInOneInstall.exe`).

**First run asks for install drive/folder** (non-C drive preferred, e.g. `D:\JinFrameAI`). ComfyUI and **models** go there to avoid filling C::

```text
D:\JinFrameAI\
  ComfyUI\ComfyUI\          ← app + workflows
  ComfyUI\ComfyUI\models\   ← weights (largest)
  tools\Python312\          ← if no suitable system Python
  tools\Git\
```

Command line:

```powershell
allInOneInstall\AllInOneInstall.exe --install-root=E:\AI\JinFrame
```

The installer checks/installs Git, Python, optional Node.js, then ComfyUI, JinFrame Assistant, and workflow sync. You can launch ComfyUI at the end.

Paths are saved to `jinframe_install_paths.json` (gitignored) for the next run.

### 1. Clone this repo

```powershell
git clone https://github.com/tigerStl/jinFrameComfyUI.git
cd jinFrameComfyUI
```

### 2. Install ComfyUI (pinned version)

Tested on **ComfyUI v0.21.1** ([Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI)), defined in **`COMFYUI.lock.json`**.  
The ComfyUI **app is not stored in Git**; `setup_comfyui.ps1` clones the locked revision locally.

**Option A — `comfyui` next to the repo (default)**

```powershell
.\install\setup_comfyui.ps1
$env:COMFYUI_ROOT = (Resolve-Path .\comfyui\ComfyUI).Path
```

**Option B — separate path**

```powershell
.\install\setup_comfyui.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI"
$env:COMFYUI_ROOT = "D:\ComfyUI\ComfyUI"
```

Installs **ComfyUI-Manager**, **ComfyUI-GGUF**, **ComfyUI_LTX2_SM**, etc. (see lock file).

**Start ComfyUI (8GB GPU example)**

```powershell
cd $env:COMFYUI_ROOT
python main.py --lowvram
```

Official Windows portable builds may use:

```powershell
.\python_embeded\python.exe main.py --lowvram
```

For tight VRAM on Hunyuan, add `--cpu-vae` (see per-workflow notes).

**Already have ComfyUI?** Match `COMFYUI.lock.json` or re-run `setup_comfyui.ps1 -ComfyRoot "your\path"`.

### 3. Assistant, workflows, models

```powershell
.\install\install_jinframe_assistant.ps1 -ComfyRoot $env:COMFYUI_ROOT
.\install\sync_to_comfyui.ps1 -ComfyRoot $env:COMFYUI_ROOT
```

Download weights per **[MODELS.md](MODELS.md)** or **one-click** in the Assistant.

Restart ComfyUI → **💬** → open JSON under sidebar `workflows`.

### 4. Pick a workflow by task

| Goal | Open |
|------|------|
| Try FLUX T2I | `Flux_Sample_T2I.json` |
| East Asian portrait | `SDXL_AWPortraitXL_国人肖像.json` |
| Look-dev I2I | `Flux_I2I_定妆照参考.json` |
| 8GB I2V short clip | `I2V_标准_图生视频_稳态少虚影.json` |
| High-quality LTX (large VRAM) | `ltx23_i2v distilled.json` or `ltx云GPU/` |
| Multi-shot short | `wan视频流/00_分镜流程说明.md` |

### 5. (Optional) Edit workflows via chat

1. Set `JINFRAME_REPO_ROOT` to this repo root.  
2. Enable **Cursor Agent** in the Assistant and save API key.  
3. Describe node/resolution/frame changes; then `sync_to_comfyui.ps1` or Reload in ComfyUI.

---

## Why ComfyUI is not inside this Git repo

| Reason | Explanation |
|--------|-------------|
| Size | ComfyUI + custom nodes + `models` can be tens of GB |
| Updates | Upstream moves fast; **`COMFYUI.lock.json`** pins a **tested commit** |
| Weights | Still downloaded separately (`MODELS.lock.json` / **MODELS.md**) |

Your install lives under `comfyui\ComfyUI` (default) or `-ComfyRoot` — never pushed by `git push`.

---

## Directory layout

| Path | Role |
|------|------|
| **Repo root** | Workflows, `install/`, JinFrame extension, `COMFYUI.lock.json`, `MODELS.lock.json` |
| **ComfyUI install** | Runtime from `setup_comfyui.ps1` (default `comfyui\ComfyUI`, gitignored) |
| **Workflow backup (optional)** | Pruned JSON; copy back to `workflows\` when needed |

Folder index: `workflows/工作流目录说明.md` (Chinese filenames in tree; JSON names are self-describing).

---

## Preset workflows (detailed)

| Category | File | Summary |
|----------|------|---------|
| FLUX T2I | `Flux_Sample_T2I.json` | FLUX T2I starter |
| FLUX T2I | `Flux_T2I_风格_清冷高级.json` | Cool, high-end portrait style |
| FLUX I2I | `Flux_I2I_定妆照参考.json` | Look-dev: lock face, change scene |
| FLUX I2I | `FLUX_人像写实化_I2I.json` | De-AI / photoreal polish |
| FLUX T2I | `Flux_T2I_惊悚_大厅走廊.json` | Psychological horror empty shot |
| FLUX I2I | `Flux_人物场景融合_单人.json` | Composite person into horror scene |
| SDXL T2I | `SDXL_AWPortraitXL_国人肖像.json` | East Asian realistic portrait |
| Hunyuan T2I | `HunyuanDiT_T2I_中国风格.json` | Layered Chinese T2I |
| Hunyuan I2I | `HunyuanDiT_图形合成_02_图生图.json` | Reference background swap |
| Kolors T2I | `Kolors_T2I_惊悚_场景.json` | Chinese horror scene |
| Wan I2V | `I2V_标准_图生视频_稳态少虚影.json` | 8GB I2V, less ghosting |
| Wan S2V | `Wan22_S2V_有声图生视频_简版.json` | Image + audio video |
| Wan storyboard | `wan视频流/02_Wan_片段_A_kf01到kf02.json` | Segment between keyframes |
| LTX local | `ltx23_i2v distilled.json` / `ltx23_t2v distilled.json` | Distilled I2V/T2V |
| LTX cloud | `ltx云GPU/LTX23_云GPU_*_distilled_fp8.json` | Cloud fp8 I2V/T2V |
| LTX storyboard | `ltx视频流/02_LTX_片段_A_首尾_kf01到kf02.json` | First/last frame segment |
| LTX template | `LTX_Template_首帧.json` | Single-frame micro-motion |
| Post | `后处理_脸部局部亮度.json` | Face brightness tweak |

---

### FLUX · image

#### `Flux_Sample_T2I.json` — FLUX T2I (general)

| Item | Notes |
|------|-------|
| **Use** | Standard FLUX.1 Dev wiring; any subject |
| **Pipeline** | `flux1-dev-fp8` + CLIP/T5 + VAE → encode → **FluxGuidance** → KSampler (**CFG must be 1.0**) |
| **Default size** | 768×1024 portrait |
| **Key** | FluxGuidance **3.5**; ~**28** steps; euler / simple |
| **Pack** | Assistant → **FLUX T2I/I2I** |
| **Note** | Do not use CFG 7–12 (SDXL habit); FLUX uses FluxGuidance |
| **Next** | Look-dev, keyframes, or I2V pipelines |

#### `Flux_T2I_风格_清冷高级.json` — Cool high-end style

| Item | Notes |
|------|-------|
| **Use** | Fixed cool, restrained East Asian female portrait + low-sat horror ambience |
| **Style** | Cold skin, thin lips, distant eyes, minimal makeup, shirt/skirt, stairwell fluorescent |
| **Key** | FluxGuidance **3.6**; negative blocks thick lips, sweet idol look, heavy makeup |
| **Size** | 768×1024 |
| **Chain** | → `Flux_I2I_定妆照参考` → `Flux_人物场景融合_单人` → `wan视频流` / `ltx视频流` |

#### `Flux_I2I_定妆照参考.json` — Look-dev I2I

| Item | Notes |
|------|-------|
| **Use** | Upload **Chinese face close-up**; keep identity, change background/light/makeup |
| **Input** | Clear frontal look-dev in `ComfyUI/input/` |
| **Key** | **denoise 0.50–0.56** (0.55 keeps face; 0.7 changes background more); FluxGuidance 3.8 |
| **Chain** | → `FLUX_人像写实化_I2I` → face post → video keyframes |

#### `FLUX_人像写实化_I2I.json` — Photoreal polish

| Item | Notes |
|------|-------|
| **Use** | Push anime/plastic skin toward documentary RAW photo |
| **Key** | **denoise 0.40–0.48**; negative: anime, manga, plastic doll skin |
| **Chain** | After SDXL or look-dev I2I |

#### `Flux_T2I_惊悚_大厅走廊.json` — Horror empty shot

| Item | Notes |
|------|-------|
| **Use** | **No people** — corridors, symmetry, doors, EXIT lights, reflections |
| **Size** | **1344×768** landscape |
| **Key** | FluxGuidance **3.7**; J-horror, non-gory |
| **Chain** | Scene ref for `Flux_人物场景融合_单人` or micro-motion I2V |

#### `Flux_人物场景融合_单人.json` — Person into scene

| Item | Notes |
|------|-------|
| **Use** | Merge **look-dev** + **empty scene** into one cinematic still |
| **Inputs** | ① Person A ② Person B (0 blend for solo) ③ Scene reference |
| **Solo** | AB blend **0**; coarse blend **0.28–0.38**; denoise **0.50–0.56** |
| **Output** | `output/sample/flux_jhorror_compose/` → copy to `input/keyframe/kf_01.png` |
| **Note** | Read the in-graph **usage** node after load |

---

### SDXL · image

#### `SDXL_AWPortraitXL_国人肖像.json`

| Item | Notes |
|------|-------|
| **Use** | **AWPortrait XL 1.1** — East Asian realistic T2I |
| **Pipeline** | Checkpoint → CN/EN prompt → KSampler (**cfg ≈ 3**, dpmpp_2m) |
| **Size** | 768×1152 |
| **Pack** | **SDXL portrait** or `install\install_sdxl_asian.ps1` |
| **Chain** | → face post → Wan/LTX keyframes |

---

### Hunyuan DiT · Chinese image

#### `HunyuanDiT_T2I_中国风格.json`

| Item | Notes |
|------|-------|
| **Use** | Native **Chinese prompts** for cinematic / suspense stills |
| **8GB** | steps **28**, cfg **6**; start with `--lowvram --cpu-vae` |
| **Pack** | **Hunyuan DiT** |
| **Note** | Queue either this or `图形合成_02`, not both merged with old 01 |

#### `HunyuanDiT_图形合成_02_图生图.json`

| Item | Notes |
|------|-------|
| **Use** | Keep pose/identity; replace background/mood |
| **vs 01** | `01` is T2I only; **02** is I2I (canonical) |
| **Doc** | `workflows/HunyuanDiT_图形合成_README.md` |

---

### Kolors · Chinese image

#### `Kolors_T2I_惊悚_场景.json`

| Item | Notes |
|------|-------|
| **Use** | Kwai **Kolors** Chinese T2I for horror scenes |
| **Deps** | ChatGLM3 encoder; **ComfyUI-KwaiKolorsWrapper** via Manager |
| **Chain** | Scene → slot ③ in `Flux_人物场景融合_单人` |

---

### Wan 2.2 · video

#### `I2V_标准_图生视频_稳态少虚影.json` — 8GB I2V

| Item | Notes |
|------|-------|
| **Use** | **Single first frame** → ~3s micro-motion; less blur/ghosting on 8GB |
| **Default** | 768×432, **49** frames, Lightning 4-step LoRA **0.6** |
| **Prompt** | Breathing, blink, tiny motion only — **no** turn / walk / spin / big camera moves |
| **Pack** | **Wan 2.2 I2V (8GB)** + **ComfyUI-GGUF** |
| **Doc** | `workflows/I2V_Wan_README.md` |

#### `Wan22_S2V_有声图生视频_简版.json` — S2V

| Item | Notes |
|------|-------|
| **Use** | **Face + audio** → lip-sync / rhythm |
| **Default** | ~**77** frames @ 16fps (~4.8s) |
| **VRAM** | **16GB+** recommended; 8GB often OOM |
| **Install** | `install\install_wan22_s2v.ps1` |
| **Doc** | `workflows/Wan_S2V_README.md` |

#### `wan视频流/02_Wan_片段_A_kf01到kf02.json` — Storyboard segment A

| Item | Notes |
|------|-------|
| **Use** | Step 2: **kf_01** → **seg_A** micro-motion |
| **Prep** | `01_FLUX_关键帧_三连图` or FLUX/SDXL → `input/keyframe/` |
| **Doc** | `wan视频流/00_分镜流程说明.md` |

---

### LTX 2.3 · video

#### `ltx23_i2v distilled.json` / `ltx23_t2v distilled.json`

| Item | Notes |
|------|-------|
| **Use** | Local LTX 2.3 with **distill LoRA** for fewer steps |
| **VRAM** | **16GB+**; on 8GB prefer Wan storyboard or lower res |
| **LoRA** | Synced from `distill_loras/` via `sync_to_comfyui.ps1` |
| **RTX 50** | Run `patch_ltx2_sm_pytorch_attention.py` if attention errors |

#### `ltx云GPU/LTX23_云GPU_I2V_distilled_fp8.json` / T2V variant

| Item | Notes |
|------|-------|
| **Use** | **24GB+** cloud GPU; fp8 dev + distill LoRA |
| **Install** | `install\install_ltx23_dev_fp8_download.ps1` |
| **Note** | Different graph from `ltx视频流` GGUF — do not mix in one queue |

#### `ltx视频流/02_LTX_片段_A_首尾_kf01到kf02.json`

| Item | Notes |
|------|-------|
| **Use** | **kf_01 → kf_02** transition; good for turns vs Wan single-frame |
| **Doc** | `ltx视频流/00_分镜流程说明.md` |

#### `LTX_Template_首帧.json`

| Item | Notes |
|------|-------|
| **Use** | One image locked as first frame; minimal motion |
| **Chain** | Related to `ltx视频流/02_LTX_起始帧_锁定kf01`; long edits still use A/B segments |

---

### Post-processing

#### `后处理_脸部局部亮度.json`

| Item | Notes |
|------|-------|
| **Use** | No diffusion — face exposure/contrast with mask |
| **Input** | Portrait + `face_mask.png` (white = adjust) |
| **Doc** | `workflows/后处理_脸部局部亮度_README.md` |

---

### Example production chains

```text
[Character stills] Flux_T2I_风格_清冷高级 → Flux_I2I_定妆照参考 → face brightness post
[Empty scenes]     Flux_T2I_惊悚_大厅走廊 or Kolors/Hunyuan scene T2I
[Person in scene]  Flux_人物场景融合_单人 → kf_01.png
[8GB short film]   wan视频流: keyframes → segments → concat_segments.ps1
[HQ long takes]    ltx视频流 or ltx云GPU; 16GB+ for ltx23_* distilled
[Audio shot]       Wan22_S2V_简版 (16GB+)
```

---

## Install scripts & tools (advanced)

Run from repo root in PowerShell:

| Script | Purpose |
|--------|---------|
| `install\setup_comfyui.ps1` | Install ComfyUI v0.21.1 + required nodes from lock |
| `install\generate_comfyui_lock.py` | Maintainer: export new ComfyUI lock from local install |
| `install\sync_to_comfyui.ps1` | Sync workflows; optional distill LoRA |
| `install\install_jinframe_assistant.ps1` | Install JinFrame Assistant |
| `install\install_flux_schnell_fp8.ps1` | FLUX Schnell fp8 assets |
| `install\install_sdxl_asian.ps1` | SDXL portrait assets |
| `install\install_hunyuan_dit.ps1` | Hunyuan DiT assets |
| `install\install_kolors.ps1` | Kolors nodes/weights |
| `install\install_wan22_i2v_gguf.ps1` | Wan 2.2 I2V GGUF stack |
| `install\install_wan22_s2v.ps1` | Wan S2V stack |
| `install\install_ltx23_dev_fp8_download.ps1` | LTX 2.3 fp8 + encoders |
| `install\patch_ltx2_sm_pytorch_attention.py` | RTX 50 / sm_120 attention fix for LTX2_SM |
| `install\sanitize_workflow_prompts.py` | Sanitize positive prompts in JSON |
| `install\prune_workflows.py` | Move non-canonical workflows to backup (`--dry-run`) |
| `install\download_from_lock.py` | Download from `MODELS.lock.json` |
| `install\verify_models.py` | Verify SHA256 / size |
| `install\generate_models_lock.py` | Maintainer: refresh model lock |

Workflows only:

```powershell
.\install\sync_to_comfyui.ps1 -WorkflowsOnly
```

---

## VRAM & hardware

| Scenario | Guidance |
|----------|----------|
| FLUX / SDXL stills | 8GB with fp8 / lower res; 16GB more comfortable |
| Wan 2.2 I2V GGUF | **8GB** target; short segments + keyframes |
| LTX 2.3 local distilled | **16GB+** + distill LoRA |
| LTX 2.3 cloud fp8 | **24GB+** |
| RTX 50 (e.g. 5060) | LTX attention errors → `patch_ltx2_sm_pytorch_attention.py` |

Use `python main.py --lowvram` when starting ComfyUI.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `JINFRAME_REPO_ROOT` | This repo root (Assistant / Cursor Agent) |
| `COMFYUI_ROOT` | ComfyUI install (contains `main.py`, `models\`) |

---

## Model installation

- Large weights are **not** in Git — follow **[MODELS.md](MODELS.md)**.  
- **Easiest:** JinFrame Assistant → model packs → **one-click download**.  
- **Script:** `python install\download_from_lock.py --pack <pack_id>` then `python install\verify_models.py`.  
- Set `COMFYUI_ROOT` before running scripts.  
- LTX distill LoRA may copy from `distill_loras\` when running `sync_to_comfyui.ps1` if present locally.

---

## Copyright & license

- **This repository** (workflow JSON, `install/` scripts, JinFrame Assistant extension, documentation): **Copyright © 2026 Gengfeng Liu / 金帧AI工作室**, licensed under the **[Apache License 2.0](LICENSE)**. Redistributions should include [NOTICE](NOTICE).
- **Third-party model weights** (FLUX, Wan, LTX, Hunyuan, Kolors, SDXL checkpoints, etc.) are **not** bundled here; each has its own license. LTX terms: [licenses/LTX-2-Community-License.txt](licenses/LTX-2-Community-License.txt). See **[MODELS.md](MODELS.md)** for download and compliance notes.
