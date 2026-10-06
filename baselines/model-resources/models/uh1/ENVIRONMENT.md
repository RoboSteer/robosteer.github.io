> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 环境配置

本记录来自 <HOST> 上已有、已被历史批处理使用的 `UH-1` Conda 环境；没有在全新机器逐条验证安装过程。推理与转换共用此环境，转换另需 GMR 包和 G1 资源（见 [`RESOURCES.md`](RESOURCES.md)）。

| 项目 | 记录值 |
| --- | --- |
| 系统 | Ubuntu 22.04，x86_64 |
| GPU | Tesla V100-SXM2-16GB（本机两张） |
| Python | 3.8.11 |
| PyTorch / torchvision | 2.4.1 / 0.19.1 |
| NumPy | 1.24.4 |
| MuJoCo | 3.2.3 |
| OpenAI CLIP | Git commit `d05afc436d78f1c48dc0dbf8e5980a9d471f35f6` |
| 其他实测环境包 | `ftfy==6.2.3`、`regex==2024.11.6`、`opencv-python==5.0.0.93`、`tqdm==4.68.3` |

推荐先建立独立环境，并选择与本机 CUDA 驱动兼容的 PyTorch 2.4.1 构建：

```bash
conda create -n UH-1 python=3.8.11
conda activate UH-1
python -m pip install numpy==1.24.4 torch==2.4.1 torchvision==0.19.1 mujoco==3.2.3
python -m pip install ftfy==6.2.3 regex==2024.11.6 tqdm==4.68.3
python -m pip install 'git+https://github.com/openai/CLIP.git@d05afc436d78f1c48dc0dbf8e5980a9d471f35f6'
```

`opencv-python` 是本机环境库存的一部分，但本教程中的两个批量推理入口和 CSV 转换器未直接导入它；使用上游可视化入口时再安装。首次使用 `clip.load("ViT-B/32")` 会下载模型，离线机器需提前缓存。不要将上游 RL/Isaac Gym 环境要求混入本推理环境；本交付不运行 RL 策略。

检查：

```bash
python -c 'import torch,numpy,clip,mujoco; print(torch.__version__, numpy.__version__, mujoco.__version__, torch.cuda.is_available())'
python scripts/inference.py --help
python scripts/inference_pred.py --help
python scripts/convert_h1_to_g1_sonic.py --help
```

以上 `--help` 只验证 CLI 能加载，不代表权重、外部 G1 资源或一条完整轨迹已通过。若实际安装得到的版本与表格不同，记录在自己的运行说明中；不要把环境库存当作已验证的跨机器锁文件。
