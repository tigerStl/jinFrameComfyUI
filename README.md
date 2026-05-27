<p align="center">
  <img src="jinZhenLogo.png" alt="金帧 AI 视频平台" width="280" />
</p>

# 金帧AI视频平台_ComfyUI

**金帧 AI 视频平台**是一套面向 ComfyUI 的**图像 + 视频**生产方案：预置可直接运行的标准工作流、一键模型下载、工作流同步与安全清理工具，并内置 **金帧助手** 面板，让不熟悉命令行的用户也能在界面里完成「下模型 → 开工作流 → 对话改流程」。

> **English:** [README.en.md](README.en.md) — full platform guide, quick start, and preset workflow reference.

> 模型文件（`.safetensors` / `.gguf`）体积较大，需单独下载。平台已为各工作流锁定固定版本，安装与校验步骤见 **[模型安装说明（MODELS.md）](MODELS.md)**。

---

## 平台能做什么

> 每个标准 JSON 的用途、参数与衔接说明见下文 **[预设流程详细说明](#预设流程详细说明)**。

### 图像生成（静帧 / 定妆 / 合成）

| 能力 | 说明 | 典型工作流 |
|------|------|------------|
| **文生图 T2I** | 根据文字提示出图；含通用样例与「清冷高级」等风格模板 | `Flux_Sample_T2I.json`、`Flux_T2I_风格_清冷高级.json` |
| **图生图 I2I** | 以参考图为基础改妆造、换背景、写实化人像 | `Flux_I2I_定妆照参考.json`、`FLUX_人像写实化_I2I.json` |
| **人物 + 场景融合** | 保留人物身份，将背景换成指定场景（惊悚走廊、楼梯间等） | `Flux_人物场景融合_单人.json` |
| **国人肖像** | SDXL + 国人肖像 Checkpoint，适合证件照感、写实人像 | `SDXL_AWPortraitXL_国人肖像.json` |
| **中文审美 T2I** | Hunyuan DiT 中文提示与国画/现代混合风格 | `HunyuanDiT_T2I_中国风格.json` |
| **图形合成 I2I** | 在参考图基础上做分层式中文 prompt 合成 | `HunyuanDiT_图形合成_02_图生图.json` |
| **Kolors 中文场景** | 快手 Kolors 栈，适合中文场景与惊悚空镜 | `Kolors_T2I_惊悚_场景.json` |
| **惊悚场景 T2I** | FLUX 大厅/走廊等心理惊悚空镜与人物构图 | `Flux_T2I_惊悚_大厅走廊.json` |

### 视频生成（图生视频 / 文生视频 / 有声）

| 能力 | 说明 | 典型工作流 |
|------|------|------------|
| **Wan 2.2 图生视频** | GGUF 量化，面向 **约 8GB 显存**；含稳态少虚影调参 | `I2V_标准_图生视频_稳态少虚影.json` |
| **Wan 2.2 有声图生视频** | 图 + 音频驱动口型/节奏（S2V 简版） | `Wan22_S2V_有声图生视频_简版.json` |
| **LTX 2.3 本地** | 高质量 I2V / T2V；配合蒸馏 LoRA 可加速 | `ltx23_i2v distilled.json`、`ltx23_t2v distilled.json` |
| **LTX 2.3 云 GPU** | fp8 权重，适合 **24GB+ 显存** 或云端 GPU | `workflows/ltx云GPU/LTX23_云GPU_*` |
| **LTX 首帧模板** | 固定首帧、尾帧、起始帧等镜头衔接模板 | `LTX_Template_首帧.json` 等 |

### 分镜与长片流程（推荐工作方式）

平台不强迫「一段视频里完成复杂运镜」。对 **8GB 显存** 更稳妥的做法是：

1. **定妆 / 关键帧**：用 FLUX 或 SDXL 一次或链式生成 `kf_01`、`kf_02`… 静图  
2. **短片段**：用 Wan 或 LTX 在相邻关键帧之间生成数秒片段  
3. **拼接**：用 ffmpeg 或仓库内说明脚本合成 `final.mp4`  

分镜示例与步骤说明：

- `workflows/wan视频流/` — Wan 片段 + `00_分镜流程说明.md`  
- `workflows/ltx视频流/` — LTX 片段 + `00_分镜流程说明.md`  

### 后处理

| 能力 | 说明 |
|------|------|
| **脸部局部亮度** | 在成片或静图上对面部区域做亮度/对比微调，减轻过暗或过曝 | `后处理_脸部局部亮度.json` |

### 工作流治理（维护与安全）

| 功能 | 作用 |
|------|------|
| **标准工作流集** | 每类「模型 × 流程」只保留 **一份** canonical JSON，避免重复版本混淆 |
| **同步到 ComfyUI** | 将 `workflows/` 一键复制到 ComfyUI 侧栏目录，改完即刷新生效 |
| **Prompt 安全清理** | 扫描 JSON，替换不当或露骨**正向**提示词；保留负向里的 `nsfw` 等屏蔽项 |
| **工作流精简** | 将非标准、重复、测试版 JSON 移到本机备份目录（不进 Git） |

---

## 金帧助手（ComfyUI 内置面板）

面向**不想手写 PowerShell** 的用户。安装后 ComfyUI 界面**右侧**出现蓝色 **💬** 按钮。

```powershell
.\install\install_jinframe_assistant.ps1
# 安装后请完全退出并重启 ComfyUI
```

### 面板功能一览

| 区域 | 功能 |
|------|------|
| **模型包** | 按 FLUX / SDXL / Hunyuan / Kolors / Wan / LTX 分组；勾选文件后 **一键下载** 到 ComfyUI `models\` 对应子目录 |
| **下载状态** | 显示本地是否已有权重、体积是否达标；大文件支持断点续传式拉取 |
| **Cursor Agent** | 勾选并保存 **Cursor API Key** 后，对话可让 Agent **直接改本仓库** 的 `workflows/`（需配置 `JINFRAME_REPO_ROOT`） |
| **本地对话** | 关闭 Agent 时，使用本机 **Ollama + Qwen** 解答用法与参数（`ollama pull qwen2.5:7b`） |
| **配置存储** | API Key 等保存在本机 `ComfyUI\user\default\jinframe_assistant_config.json`，不上传仓库 |

### 助手支持的模型包（与标准工作流对应）

- **FLUX 文生图 / 图生图** — UNet fp8、CLIP、T5、VAE  
- **SDXL 国人肖像** — AWPortrait XL  
- **Hunyuan DiT 中文** — 1.2 checkpoint  
- **Kolors 中文 T2I** — ChatGLM3 等（需 ComfyUI-Manager 安装 Kolors 节点）  
- **Wan 2.2 图生视频 (8GB)** — 高低噪声 GGUF、编码器、VAE、LightX2V LoRA（需 ComfyUI-GGUF）  
- **LTX 2.3 云 GPU (fp8)** — dev fp8、Gemma 文本编码器、蒸馏 LoRA（建议 24GB+ 显存）

清单细节见 `comfyui_extension/ComfyUI_JinFrameAssistant/models_manifest.json`。

---

## 快速开始（推荐顺序）

### 0. 一键安装（Windows，推荐新手）

在仓库根目录**双击**：

```text
一键安装.bat
```

或运行 `allInOneInstall\一键安装.exe`（若无中文文件名则用 `AllInOneInstall.exe`）。

**首次运行会提示选择安装盘符**（默认优先非 C 盘）。  
ComfyUI 与 **models** 装在**该盘根目录**下（与 Git 克隆目录无关），避免占满 C 盘：

```text
D:\
  ComfyUI\ComfyUI\        ← 程序与工作流（非仓库下的 comfyui 文件夹）
  ComfyUI\ComfyUI\models\ ← 模型（体积最大）
  tools\Python312\       ← 若无合适系统 Python 时安装到此
  tools\Git\
```

也可命令行指定盘符或盘根路径：

```powershell
allInOneInstall\AllInOneInstall.exe --install-root=D:
```

程序将自动检查并安装 Git、Python、可选 Node.js，再安装 ComfyUI 与金帧助手，最后询问是否启动。  
**NVIDIA 显卡**会先检测型号再安装对应 **CUDA 版 PyTorch**（RTX 3050/30/40 系 → **cu130**；RTX 5060/50 系 → **cu128 nightly**；无显卡 → CPU 模式）。启动参数含 `--lowvram --disable-cuda-malloc`。

安装结束后，在 ComfyUI 目录生成 **`启动ComfyUI.bat`**（例如 `D:\ComfyUI\ComfyUI\启动ComfyUI.bat`），并写入用户环境变量 `COMFYUI_ROOT`、`JINFRAME_REPO_ROOT` 及工具盘 Python/Git 的 PATH。**日常请双击该 bat 启动**，不要依赖安装程序窗口内的 Python。

### 1. 获取本仓库

```powershell
git clone https://github.com/tigerStl/jinFrameComfyUI.git
cd jinFrameComfyUI
```

### 2. 安装 ComfyUI（固定版本）

平台测试环境为 **ComfyUI v0.21.1**（[Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI)），版本号写在 **`COMFYUI.lock.json`** 中。  
**ComfyUI 程序本体不会提交到 Git**（体积大、更新频繁）；安装脚本会在您电脑上按锁定版本**自动克隆**。

**方式 A — 装在仓库旁的 `comfyui` 文件夹（默认，推荐新用户）**

```powershell
.\install\setup_comfyui.ps1
$env:COMFYUI_ROOT = (Resolve-Path .\comfyui\ComfyUI).Path
```

**方式 B — 装到独立目录（与官方 Windows 包目录类似）**

```powershell
.\install\setup_comfyui.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI"
$env:COMFYUI_ROOT = "D:\ComfyUI\ComfyUI"
```

脚本会安装锁定版本的 ComfyUI，以及 **ComfyUI-Manager**、**ComfyUI-GGUF**、**ComfyUI_LTX2_SM** 等节点（见 `COMFYUI.lock.json`）。

**启动 ComfyUI（8GB 显卡示例）**

```powershell
cd $env:COMFYUI_ROOT
python main.py --lowvram
```

若使用官方 **Windows 便携包**且已自带 `python_embeded\python.exe`，可在该目录下执行：

```powershell
.\python_embeded\python.exe main.py --lowvram
```

混元等工作流若显存紧张，可再加 `--cpu-vae`（见各工作流说明）。

**若您已自行安装 ComfyUI**  
请确认版本与 `COMFYUI.lock.json` 一致，或重新运行 `setup_comfyui.ps1 -ComfyRoot "您的路径"` 对齐节点与提交号。

### 3. 金帧助手、工作流与模型

```powershell
.\install\install_jinframe_assistant.ps1 -ComfyRoot $env:COMFYUI_ROOT
.\install\sync_to_comfyui.ps1 -ComfyRoot $env:COMFYUI_ROOT
```

按 **[MODELS.md](MODELS.md)** 下载所需模型（或 ComfyUI 内金帧助手 **一键下载**）。

完全退出并重启 ComfyUI → 右侧 **💬** → 在侧栏 `workflows` 打开对应 JSON。

### 4. 按任务选工作流

| 你想做… | 打开… |
|---------|--------|
| 快速试 FLUX 出图 | `Flux_Sample_T2I.json` |
| 国人写实肖像 | `SDXL_AWPortraitXL_国人肖像.json` |
| 定妆照再改造型 | `Flux_I2I_定妆照参考.json` |
| 8GB 显卡图生短视频 | `I2V_标准_图生视频_稳态少虚影.json` |
| 高质量 LTX 视频（大显存） | `ltx23_i2v distilled.json` 或 `ltx云GPU/` 下工作流 |
| 多镜头短片 | 先看 `wan视频流/00_分镜流程说明.md` |

### 5.（可选）用对话改工作流

1. 设置 `JINFRAME_REPO_ROOT` 为本仓库根目录。  
2. 在助手中启用 **Cursor Agent** 并保存 API Key。  
3. 用自然语言描述要改的节点、分辨率、帧数等；改完后再次 `sync_to_comfyui.ps1` 或直接在 ComfyUI 里 Reload。

---

## 为何 ComfyUI 不直接放在本 Git 仓库里？

| 原因 | 说明 |
|------|------|
| 体积 | ComfyUI + 自定义节点 + `models` 可达数十 GB，不适合 Git 克隆 |
| 更新 | 上游频繁发版；平台用 **`COMFYUI.lock.json`** 固定**测试通过的提交号**，避免「最新 main」导致节点不兼容 |
| 模型 | 权重仍单独下载（见 **MODELS.lock.json** / **MODELS.md**） |

您本地安装后，ComfyUI 位于 `comfyui\ComfyUI`（默认）或您指定的 `-ComfyRoot`，**不会**被 `git push` 上传。

---

## 目录约定

| 路径 | 说明 |
|------|------|
| **本仓库根目录** | 工作流、`install/`、金帧助手扩展、`COMFYUI.lock.json`、`MODELS.lock.json` |
| **ComfyUI 安装目录** | 运行环境（`setup_comfyui.ps1` 克隆；默认 `comfyui\ComfyUI`，已在 `.gitignore`） |
| **工作流备份目录（可选）** | 精简脚本移出的历史 JSON；需要时复制回 `workflows\` |

---

## 预设流程详细说明

下表为全部标准预设；各小节说明**用途、输入、输出、关键参数、模型依赖**及**与其它流程的衔接**。

| 分类 | 文件 | 一句话 |
|------|------|--------|
| FLUX T2I | `Flux_Sample_T2I.json` | 通用文生图入门 |
| FLUX T2I | `Flux_T2I_风格_清冷高级.json` | 清冷高级人像风格 |
| FLUX I2I | `Flux_I2I_定妆照参考.json` | 定妆照锁脸换背景 |
| FLUX I2I | `FLUX_人像写实化_I2I.json` | 去「AI 感」写实化 |
| FLUX T2I | `Flux_T2I_惊悚_大厅走廊.json` | 心理惊悚空镜（无人） |
| FLUX I2I | `Flux_人物场景融合_单人.json` | 人物抠图融入惊悚场景 |
| SDXL T2I | `SDXL_AWPortraitXL_国人肖像.json` | 东亚写实肖像 |
| Hunyuan T2I | `HunyuanDiT_T2I_中国风格.json` | 中文分层文生图 |
| Hunyuan I2I | `HunyuanDiT_图形合成_02_图生图.json` | 参考图换背景/融氛围 |
| Kolors T2I | `Kolors_T2I_惊悚_场景.json` | 中文惊悚场景 |
| Wan I2V | `I2V_标准_图生视频_稳态少虚影.json` | 8GB 图生短视频（少重影） |
| Wan S2V | `Wan22_S2V_有声图生视频_简版.json` | 图+音频有声视频 |
| Wan 分镜 | `wan视频流/02_Wan_片段_A_kf01到kf02.json` | 关键帧间稳态片段 |
| LTX 本地 | `ltx23_i2v distilled.json` / `ltx23_t2v distilled.json` | 本地蒸馏 I2V/T2V |
| LTX 云 | `ltx云GPU/LTX23_云GPU_*_distilled_fp8.json` | 云端 fp8 高质量视频 |
| LTX 分镜 | `ltx视频流/02_LTX_片段_A_首尾_kf01到kf02.json` | 首尾帧补间片段 |
| LTX 模板 | `LTX_Template_首帧.json` | 单图锁首帧微动 |
| 后处理 | `后处理_脸部局部亮度.json` | 脸部亮度微调 |

目录树见 `workflows/工作流目录说明.md`；分镜子目录另有 `00_分镜流程说明.md`。

---

### FLUX · 图像

#### `Flux_Sample_T2I.json` — FLUX 文生图（通用样例）

| 项目 | 说明 |
|------|------|
| **用途** | 学习 FLUX.1 Dev 在 ComfyUI 中的标准接法；任意主题文生图 |
| **流程** | 加载 `flux1-dev-fp8` + CLIP/T5 + VAE → 正向/负向编码 → **FluxGuidance** → KSampler（**CFG 必须为 1.0**）→ 出图 |
| **默认画幅** | 768×1024（竖幅人像） |
| **关键参数** | FluxGuidance **3.5**；步数约 **28**；采样器 euler / simple |
| **模型包** | 金帧助手 → **FLUX 文生图 / 图生图** |
| **注意** | KSampler 的 CFG 勿改成 7–12，那是 SDXL 习惯；FLUX 靠 FluxGuidance 控风格 |
| **下游** | 出图可作定妆、关键帧，或接 `Flux_I2I_*` / 视频流程 |

---

#### `Flux_T2I_风格_清冷高级.json` — 风格文生图：清冷高级

| 项目 | 说明 |
|------|------|
| **用途** | 固定「清冷、高级、禁欲感」东亚女性人像 + 低饱和惊悚环境；比 Sample 更省改 prompt |
| **风格要点** | 正向已写：冷白皮、薄唇、丹凤眼疏离、极简妆、白衬衫灰裙、居民楼楼梯间冷荧光灯 |
| **关键参数** | FluxGuidance **3.6**；负向屏蔽厚唇、甜美笑、日系偶像风、浓妆 |
| **默认画幅** | 768×1024 |
| **适用** | 角色设定图、海报静帧、分镜 **kf_01** 正面定妆 |
| **衔接** | → `Flux_I2I_定妆照参考` 精修 → `Flux_人物场景融合_单人` 入景 → `wan视频流` / `ltx视频流` |

---

#### `Flux_I2I_定妆照参考.json` — 图生图：定妆照锁脸

| 项目 | 说明 |
|------|------|
| **用途** | 上传**中国人脸部特写定妆照**，在**保持同一人五官**前提下换背景、补光影、微调妆造 |
| **输入** | `LoadImage`：正脸清晰、光线均匀的定妆照（建议放入 `ComfyUI/input/`） |
| **流程** | 参考图 VAEEncode → I2I KSampler → 解码保存 |
| **关键参数** | **denoise 0.50–0.56**（节点标注：0.55 保脸，0.7 背景变化大）；FluxGuidance 3.8 |
| **正向要点** | 强调 `same person`、仅改 Background；惊悚楼梯间、冷荧光灯 |
| **推荐** | 比纯 T2I 更易保持脸型一致；是分镜流程的 **reference / kf_01** 来源 |
| **衔接** | → `FLUX_人像写实化_I2I` 去 AI 感 → `后处理_脸部局部亮度` → 视频关键帧 |

---

#### `FLUX_人像写实化_I2I.json` — 图生图：人像写实化

| 项目 | 说明 |
|------|------|
| **用途** | 把偏动漫、塑料皮肤、过度磨皮的图，拉向**纪录片式 RAW 写真** |
| **输入** | 上传「偏 AI / 动漫感」的人像 |
| **关键参数** | **denoise 0.40–0.48**（过高易换脸）；负向含 anime、manga、plastic doll skin |
| **正向要点** | 保留身份；自然毛孔、发丝、85mm 景深、轻微胶片颗粒 |
| **适用** | SDXL/FLUX 初稿不满意肤质时；出图再进融合或视频流程 |
| **衔接** | 常与 `SDXL_AWPortraitXL` 或 `Flux_I2I_定妆照参考` 串联使用 |

---

#### `Flux_T2I_惊悚_大厅走廊.json` — 文生图：心理惊悚空镜

| 项目 | 说明 |
|------|------|
| **用途** | 生成**无人物**的日系心理惊悚场景：长走廊、对称透视、门列、EXIT 灯、地面反光 |
| **风格** | J-horror：低饱和、荧光灯+深阴影、35mm 颗粒、liminal 不安感；**非血腥** |
| **默认画幅** | **1344×768** 横构图（适合视频首帧/空镜） |
| **关键参数** | FluxGuidance **3.7** |
| **衔接** | 出图作为 `Flux_人物场景融合_单人` 的 **③ 场景参考**；或作 Wan/LTX 空镜微动片段 |

---

#### `Flux_人物场景融合_单人.json` — 图生图：人物融入惊悚场景

| 项目 | 说明 |
|------|------|
| **用途** | 将**人物定妆图**与**空景场景图**合成一张「人已在场景中」的电影静帧 |
| **输入槽位** | ① 人物 A（主角色）② 人物 B（单人时 AB 融合=0）③ 场景参考（空镜 T2I 或实拍） |
| **流程** | 人物粗叠 → 与场景 ImageBlend → FLUX I2I 融景（CFG=1，denoise 融景保脸） |
| **单人参数** | AB blend **0**；人物+场景粗叠 **0.28–0.38**；denoise **0.50–0.56** |
| **双人** | AB 融合 0.35–0.48；需改正向为「双人」段（节点内有说明） |
| **输出** | `output/sample/flux_jhorror_compose/` |
| **衔接** | 合成图复制为 `input/keyframe/kf_01.png` → `wan视频流` / `ltx视频流` |

画布内 **「使用说明」** 节点含完整操作表，加载后请先阅读。

---

### SDXL · 图像

#### `SDXL_AWPortraitXL_国人肖像.json` — 东亚写实肖像

| 项目 | 说明 |
|------|------|
| **用途** | 使用 **AWPortrait XL 1.1** checkpoint，专东亚面孔、证件照/写真感写实 T2I |
| **流程** | CheckpointLoader → 中英文 prompt → KSampler（**cfg ≈ 3**，dpmpp_2m） |
| **默认画幅** | 768×1152 |
| **模型包** | 金帧助手 → **SDXL 国人肖像**；或 `install\install_sdxl_asian.ps1` |
| **负向** | 低质量、动漫、厚唇、nsfw 等 |
| **适用** | 国人肖像定稿；与 FLUX 相比更「传统 SDXL」肤质；8GB 可 `--lowvram` |
| **衔接** | → `后处理_脸部局部亮度`；或导出关键帧进 Wan/LTX |

---

### Hunyuan DiT · 中文图像

#### `HunyuanDiT_T2I_中国风格.json` — 中文文生图

| 项目 | 说明 |
|------|------|
| **用途** | **原生中文 prompt** 的悬疑/电影静帧；主体+环境+光影+构图分层描述 |
| **流程** | `hunyuan_dit_1.2.safetensors` → 双 CLIP 编码 → KSampler |
| **8GB 建议** | steps **28**、cfg **6**；启动 ComfyUI 加 `--lowvram --cpu-vae` |
| **模型包** | **Hunyuan DiT 中文** |
| **适用** | 不擅长写英文 prompt 时；中国场景、居民楼、冷色荧光等 |
| **衔接** | 与 `HunyuanDiT_图形合成_02` 二选一 Queue，勿同时开合并旧版 |

---

#### `HunyuanDiT_图形合成_02_图生图.json` — 参考图换背景

| 项目 | 说明 |
|------|------|
| **用途** | 上传参考人像，**保持姿势与身份**，仅替换背景/氛围（惊悚场景、冷色光等） |
| **流程** | LoadImage → VAEEncode → KSampler → VAEDecode → SaveImage |
| **与 01 区别** | `图形合成_01_文生图` 为纯 T2I；本文件为 **I2I**，标准集只保留 02 |
| **8GB** | 单张约 5–12 分钟，建议 lowvram |
| **说明** | 详见 `workflows/HunyuanDiT_图形合成_README.md` |

---

### Kolors · 中文图像

#### `Kolors_T2I_惊悚_场景.json` — Kolors 中文惊悚场景

| 项目 | 说明 |
|------|------|
| **用途** | 快手 **Kolors** 中文 T2I，适合中文场景描述与惊悚空镜 |
| **依赖** | ChatGLM3 量化文本编码器；ComfyUI-Manager 安装 **ComfyUI-KwaiKolorsWrapper** |
| **模型包** | **Kolors 中文 T2I**（助手备注含节点安装提示） |
| **适用** | 需要中文 prompt、与 Hunyuan 对比风格时 |
| **衔接** | 场景图 → `Flux_人物场景融合_单人` 的 ③ 场景槽 |

---

### Wan 2.2 · 视频

#### `I2V_标准_图生视频_稳态少虚影.json` — 图生视频（8GB 推荐）

| 项目 | 说明 |
|------|------|
| **用途** | **单张首帧**生成约 3 秒微动视频；针对 8GB 显存优化，减轻糊与重影 |
| **与标准版** | 比 `I2V_标准_图生视频.json` LoRA 更低（**0.6**）、prompt 更严 |
| **默认** | 768×432，**49 帧**，Lightning 4-step LoRA |
| **输入** | 首帧与输出比例一致，避免拉伸变糊 |
| **Prompt 建议** | 只写呼吸、眨眼、极微动；**勿写** turn / walk / spin / 大运镜 |
| **模型包** | **Wan 2.2 图生视频 (8GB)** + **ComfyUI-GGUF** |
| **勿做** | 单段内 180° 转身 → 用分镜关键帧 + `wan视频流` |
| **说明** | 详见 `workflows/I2V_Wan_README.md` |

---

#### `Wan22_S2V_有声图生视频_简版.json` — 有声图生视频

| 项目 | 说明 |
|------|------|
| **用途** | **参考脸 + 音频** 驱动口型与节奏，生成带声音的短视频 |
| **流程** | LoadAudio → AudioEncoder → WanSoundImageToVideo ← LoadImage → KSampler → CreateVideo |
| **默认** | 约 **77 帧 @ 16fps**（≈4.8 秒/段） |
| **显存** | 建议 **16GB+**（14B fp8，非 GGUF）；8GB 易 OOM |
| **安装** | `install\install_wan22_s2v.ps1` |
| **说明** | 详见 `workflows/Wan_S2V_README.md` |

---

#### `wan视频流/02_Wan_片段_A_kf01到kf02.json` — 分镜：稳态片段 A

| 项目 | 说明 |
|------|------|
| **用途** | 分镜流水线**第 2 步**：用 **kf_01** 作首帧，生成 **seg_A** 微动短视频 |
| **前置** | 先用 `01_FLUX_关键帧_三连图`（同目录）或 FLUX/SDXL 产出 `kf_01.png`… 放入 `ComfyUI/input/keyframe/` |
| **参数** | 768×432，length=49，LoRA 0.6，`--lowvram` |
| **同目录** | `03_Wan_首尾帧_补间`（kf_01→kf_02 过渡，转身分镜推荐）；`concat_segments.ps1` 拼接 |
| **完整步骤** | `wan视频流/00_分镜流程说明.md` |

---

### LTX 2.3 · 视频

#### `ltx23_i2v distilled.json` — 本地图生视频（蒸馏）

| 项目 | 说明 |
|------|------|
| **用途** | 本地 **LTX 2.3** 图生视频，配合 **distill LoRA** 减少步数、加快出片 |
| **权重路线** | 与 `ltx云GPU/` 不同：本地常用 **GGUF + LTX2_SM** 或官方节点 + 蒸馏 LoRA |
| **显存** | 建议 **16GB+**；8GB 请优先 Wan 分镜或降分辨率 |
| **LoRA** | `distill_loras/ltx-2.3-22b-distilled-lora-*.safetensors` 可由 `sync_to_comfyui.ps1` 同步 |
| **衔接** | 关键帧 → I2V；或与 `ltx视频流` 首尾补间配合 |

---

#### `ltx23_t2v distilled.json` — 本地文生视频（蒸馏）

| 项目 | 说明 |
|------|------|
| **用途** | 纯文字生成短视频片段；同样使用蒸馏 LoRA 加速 |
| **适用** | 无参考图、需要空镜或氛围镜头时 |
| **注意** | RTX 50 系若报 attention 错误，运行 `install\patch_ltx2_sm_pytorch_attention.py` |

---

#### `ltx云GPU/LTX23_云GPU_I2V_distilled_fp8.json` — 云端图生视频

| 项目 | 说明 |
|------|------|
| **用途** | **24GB+** 云 GPU：官方 `ltx-2.3-22b-dev-fp8` + distill LoRA，单次试跑 I2V |
| **权重** | checkpoint fp8、Gemma 文本编码器、蒸馏 LoRA（见 `ltx云GPU/README.md`） |
| **输出** | `output/video/LTX_cloud/i2v/` |
| **安装** | `install\install_ltx23_dev_fp8_download.ps1` |
| **勿混用** | 与 `ltx视频流`（GGUF）节点不同，勿在同一 Queue 混开 |

---

#### `ltx云GPU/LTX23_云GPU_T2V_distilled_fp8.json` — 云端文生视频

| 项目 | 说明 |
|------|------|
| **用途** | 云端文生视频；模板含低分辨率生成 → 可选 latent upscale → 高分辨率 |
| **显存** | 24GB 跑 fp8；48GB 可开更高分辨率与 spatial upscaler |
| **备版** | 目录内若有 `*_base_fp8.json` 步数更多、质量更高、耗时更长 |

---

#### `ltx视频流/02_LTX_片段_A_首尾_kf01到kf02.json` — 分镜：首尾补间 A

| 项目 | 说明 |
|------|------|
| **用途** | **kf_01 → kf_02** 首尾双帧驱动 LTX 过渡（转身分镜比 Wan 稳态更合适） |
| **优势** | LTX 原生 keyframe / ImageBatch；8GB 转身分镜常优于 Wan 单帧 I2V |
| **前置** | `01_FLUX_关键帧_三连图` 产出 kf 系列 |
| **同目录** | `02_LTX_片段_B_*`、`02_LTX_单帧_稳态_*`、`concat_segments.ps1` |
| **完整步骤** | `ltx视频流/00_分镜流程说明.md`、`LTX_模型与模板对照.md` |

---

#### `LTX_Template_首帧.json` — 首帧锁定模板

| 项目 | 说明 |
|------|------|
| **用途** | **单张图片**作为首帧，生成短镜头且尽量保持画面稳定（distilled 单图保真） |
| **适用** | 开场定帧 1–2 秒、或只需极微动时 |
| **输出** | `video/LTX_首帧模板_distilled_单图保真/` |
| **衔接** | 与 `ltx视频流/02_LTX_起始帧_锁定kf01` 等同族；分镜长片仍推荐 A/B 分段 |

---

### 后处理

#### `后处理_脸部局部亮度.json` — 脸部亮度微调

| 项目 | 说明 |
|------|------|
| **用途** | **不加载扩散模型**；对肖像结果做脸部曝光/对比微调 |
| **输入** | 肖像图 + **脸部蒙版** `face_mask.png`（白=调整区，黑=保留） |
| **参数** | Brightness factor **1.05–1.18** 提亮；GrowMask / FeatherMask 避免硬边 |
| **输出** | `output/post/face_brightness/` |
| **衔接** | FLUX 定妆、SDXL 肖像出图后使用 |
| **说明** | 详见 `workflows/后处理_脸部局部亮度_README.md` |

---

### 推荐生产链路（组合示例）

```text
【静帧角色】Flux_T2I_风格_清冷高级 → Flux_I2I_定妆照参考 → 后处理_脸部局部亮度
【空镜场景】Flux_T2I_惊悚_大厅走廊 或 Kolors/Hunyuan 场景 T2I
【人景合一】Flux_人物场景融合_单人 → kf_01.png
【8GB 短片】wan视频流：关键帧 → 02/03 片段 → concat_segments.ps1
【高质量长镜】ltx视频流 或 ltx云GPU I2V；16GB+ 可用 ltx23_* distilled
【有声镜头】Wan22_S2V_有声图生视频_简版（需 16GB+）
```

---

## 安装脚本与工具（进阶）

在本仓库根目录用 PowerShell 调用：

| 脚本 / 工具 | 用途 |
|-------------|------|
| `install\setup_comfyui.ps1` | 按 `COMFYUI.lock.json` 安装 ComfyUI v0.21.1 与必需节点 |
| `install\generate_comfyui_lock.py` | 维护用：从本机 ComfyUI 导出新的版本锁定 |
| `install\sync_to_comfyui.ps1` | 同步工作流；可选同步蒸馏 LoRA |
| `install\install_jinframe_assistant.ps1` | 安装金帧助手到 `custom_nodes` |
| `install\install_flux_schnell_fp8.ps1` | FLUX Schnell fp8 相关资源 |
| `install\install_sdxl_asian.ps1` | SDXL 国人肖像相关资源 |
| `install\install_hunyuan_dit.ps1` | Hunyuan DiT 资源 |
| `install\install_kolors.ps1` | Kolors 节点与权重 |
| `install\install_wan22_i2v_gguf.ps1` | Wan 2.2 I2V GGUF 栈 |
| `install\install_wan22_s2v.ps1` | Wan 有声图生视频栈 |
| `install\install_ltx23_dev_fp8_download.ps1` | LTX 2.3 fp8 与配套编码器下载 |
| `install\patch_ltx2_sm_pytorch_attention.py` | RTX 50 系列等新显卡与 xformers 兼容补丁 |
| `install\sanitize_workflow_prompts.py` | 批量清理工作流中的不当正向 prompt |
| `install\prune_workflows.py` | 将非标准工作流移至本机备份（`--dry-run` 可预览） |
| `install\download_from_lock.py` | 按 `MODELS.lock.json` 下载锁定版本 |
| `install\verify_models.py` | 校验本机模型 SHA256 / 体积 |
| `install\generate_models_lock.py` | 维护用：根据本机已安装模型更新版本清单 |

仅同步工作流：

```powershell
.\install\sync_to_comfyui.ps1 -WorkflowsOnly
```

---

## 显存与硬件建议

| 场景 | 建议 |
|------|------|
| FLUX / SDXL 静图 | 8GB 可尝试 fp8 / 降分辨率；16GB 更从容 |
| Wan 2.2 I2V GGUF | 面向 **8GB**；用短片段 + 关键帧分镜，避免单段长镜头高运动 |
| LTX 2.3 本地 distilled | 建议 **16GB+**，并配合蒸馏 LoRA |
| LTX 2.3 云 GPU fp8 | 建议 **24GB+** 显存 |
| RTX 50 系（如 5060） | 若 LTX 报 attention 错误，运行 `patch_ltx2_sm_pytorch_attention.py` |

启动 ComfyUI 时可加 `--lowvram` 以降低显存占用。

### 从头完整测试（3050 / 5060）

在测试机上 **先 `git pull`**，确认 `nvidia-smi` 正常（若显示 **GPU is lost** 必须先重启）。

```powershell
cd K:\tiger\jinFrame\jinFrameComfyUI
.\install\full_retest.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI"
```

仅修复 CUDA / 启动脚本（不重装 ComfyUI）：

```powershell
.\install\full_retest.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI" -SkipSetup -Force
```

或：

```powershell
.\install\repair_comfyui_cuda.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI"
```

验证：`python -c "import torch; print(torch.__version__)"`  
- RTX **3050**：应为 **`2.10.0+cu130`**（不能是 `+cu128`）  
- RTX **5060**：应为 **`+cu128`** nightly  

然后双击 **`启动ComfyUI.bat`**（内含 CUDA 预检）。**不要**单独执行 `pip install -r requirements.txt`，会覆盖 CUDA 版 torch。

**安装前必须先满足驱动版本**（脚本**不会**自动装驱动，不达标会**立即退出**）：

```powershell
.\install\ensure_nvidia_driver.ps1
```

- RTX **3050 / 30–40**：驱动 **≥ 580.0**（cu130 / CUDA 13）  
- RTX **5060 / 50**：驱动 **≥ 570.0**（cu128 nightly）  

未通过时会生成说明文档：

- `docs/NVIDIA_DRIVER_UPGRADE.zh-CN.md`  
- `docs/NVIDIA_DRIVER_UPGRADE.en.md`  

按文档手动升级并**重启**后，再运行 `ensure_nvidia_driver.ps1` 或一键安装。

若已装上 `2.10.0+cu130` 但 `cudaErrorNotSupported`：先升级驱动，再 `.\install\repair_comfyui_cuda.ps1`。安装 NVIDIA 驱动时建议**只装图形驱动**，**不要勾选 NVIDIA App**（避免 `chrome_elf.dll` 权限错误）。

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `JINFRAME_REPO_ROOT` | 本仓库根目录（金帧助手、Cursor Agent 定位 `workflows/`） |
| `COMFYUI_ROOT` | ComfyUI 安装目录，默认 `C:\ComfyUI\ComfyUI` |

---

## 模型文件安装

- 克隆本仓库后，**不会**自动附带大型模型权重；请按 **[MODELS.md](MODELS.md)** 下载与您要使用的工作流对应的文件。  
- 推荐方式一：在 ComfyUI 中打开金帧助手，勾选模型包后点击 **一键下载**（版本与平台测试环境一致）。  
- 推荐方式二：在本仓库根目录执行  
  `python install\download_from_lock.py --pack <包名>`，完成后运行  
  `python install\verify_models.py` 确认文件完整。  
- 具体命令、包名对照与常见问题，均以 **MODELS.md** 为准。  
- LTX 蒸馏 LoRA 可在执行 `sync_to_comfyui.ps1` 时从仓库 `distill_loras\` 复制到 ComfyUI（若您已持有该文件）。

---

## 版权与许可

- **本仓库**（工作流 JSON、`install/` 脚本、金帧助手扩展、文档等）：**Copyright © 2026 Gengfeng Liu / 金帧AI工作室**，采用 **[Apache License 2.0](LICENSE)**；分发时请保留 [NOTICE](NOTICE) 中的归属说明。
- **第三方模型权重**（FLUX、Wan、LTX、混元、Kolors、SDXL 等 `.safetensors` / `.gguf`）**不包含在本仓库**，须遵守各模型提供方及 Hugging Face 页面上的许可；LTX 相关文本见 [licenses/LTX-2-Community-License.txt](licenses/LTX-2-Community-License.txt)。模型安装与合规说明见 **[MODELS.md](MODELS.md)**。

## 联系

- **使用问题、Bug、功能建议**：[GitHub Issues](https://github.com/tigerStl/jinFrameComfyUI/issues)
- **合作、许可与其它事务**：[tiger.saint88@gmail.com](mailto:tiger.saint88@gmail.com)（金帧AI工作室）

---

## English documentation

Full English README (platform overview, one-click install, ComfyUI setup, every preset workflow, scripts, VRAM notes): **[README.en.md](README.en.md)**
