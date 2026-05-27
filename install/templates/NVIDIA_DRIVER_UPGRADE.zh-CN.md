# NVIDIA 显卡驱动升级说明（金帧 / ComfyUI）

> 由 `install/ensure_nvidia_driver.ps1` 根据本机检测结果生成。

## 本机检测结果

| 项目 | 值 |
|------|-----|
| 检测时间 | {{CHECKED_AT}} |
| 状态 | **{{STATUS}}** |
| 显卡 | {{GPU_NAME}} |
| 当前驱动版本 | **{{DRIVER_VERSION}}** |
| 所需最低版本 | **{{MIN_VERSION}}** |
| PyTorch 配置 | {{TORCH_PROFILE}} |

{{LATEST_ONLINE}}

---

## 为什么必须升级？

ComfyUI **v0.21+** 在 RTX 30/40（如 **3050**）上需要 **PyTorch cu130（CUDA 13）**。  
Windows 上 CUDA 13 要求 **NVIDIA 驱动 >= 580.0**。

驱动过旧时会出现：

- `torch 2.10.0+cu130` 已安装，但 `torch.cuda.is_available() is False`
- `cudaErrorNotSupported` / `likely using older driver`

**反复 pip 安装 torch 无法解决，必须先升级驱动并重启。**

RTX 50 系（如 5060）使用 cu128 nightly，建议驱动 **>= 570.0**。

---

## 升级步骤（手动安装，我们不提供自动装驱动）

1. 打开 https://www.nvidia.com/Download/index.aspx
2. 选择你的显卡（如 GeForce RTX 3050）-> **Windows 10/11 64-bit** -> **Game Ready Driver**
3. 下载并运行安装程序  
   - **建议只安装「图形驱动 / Display Driver」**  
   - **不要勾选 NVIDIA App**（可避免 chrome_elf.dll / Access is denied）
4. **重启电脑**
5. 确认：

   ```powershell
   nvidia-smi
   ```

   Driver Version 应 **>= {{MIN_VERSION}}**；3050 / cu130 时 CUDA Version 建议 **13.x**

6. 回到本仓库：

   ```powershell
   cd <本仓库路径>
   .\install\ensure_nvidia_driver.ps1
   .\install\setup_comfyui.ps1 -ComfyRoot "<ComfyUI 路径>"
   ```

---

## 常见问题

| 现象 | 处理 |
|------|------|
| GPU is lost | 先重启，再 nvidia-smi |
| chrome_elf.dll / Access is denied | 取消 NVIDIA App，仅装显示驱动 |
| 远程桌面 | 可用；GPU 须在 nvidia-smi 中正常 |

英文说明: docs/NVIDIA_DRIVER_UPGRADE.en.md
