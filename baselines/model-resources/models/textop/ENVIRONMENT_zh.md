> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 环境与外部资源

## 已跑通的服务器环境

| 项目 | 参考值 |
| --- | --- |
| GPU | NVIDIA Tesla V100-SXM2-16GB |
| Python | 3.8.20 |
| PyTorch / CUDA | 2.4.1+cu121 / 12.1 |
| NumPy / SciPy | 1.24.4 / 1.10.1 |
| MuJoCo | 3.2.3 |
| Hydra / OmegaConf | 1.3.2 / 2.3.0 |

原版 TextOp 的安装步骤见[上游 USAGE.md](https://github.com/TeleHuman/TextOp/blob/main/USAGE.md)。本项目的参考环境使用了上表版本；在全新机器上安装时，请先建立独立的 Python 3.8 环境，另行取得上游源码后，从其 `TextOp/` 根目录安装 `deps/isaac_utils`、`TextOpRobotMDAR` 和上游 OpenAI CLIP。`TextOpRobotMDAR/pyproject.toml` 声明了其余 Python 依赖。当前参考包不含 TextOp 上游源码；以下版本仅记录历史文本推理环境。**全新机器从零安装尚未完整验证。**

参考安装顺序如下；请根据本机 NVIDIA 驱动选择兼容的 CUDA wheel。下面的版本与参考服务器一致，但整套命令尚未在全新机器上实测：

```bash
conda create -n textop-repro python=3.8 pip -y
conda activate textop-repro
python -m pip install torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cu121
cd TextOp
python -m pip install -e deps/isaac_utils
python -m pip install -e TextOpRobotMDAR
python -m pip install 'git+https://github.com/openai/CLIP.git@d05afc436d78f1c48dc0dbf8e5980a9d471f35f6'
python -c 'import torch, numpy, scipy, mujoco, hydra, clip, robotmdar; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())'
cd ..
```

若编译组件或依赖解析失败，先对照下方参考环境清单核对版本，不要直接把清单当安装脚本。`TextOpRobotMDAR` 依赖 MuJoCo，运行前还需确认目标机器的 OpenGL 运行库可正常加载。

历史环境包清单（含本机路径，公开版已移除） 是这台服务器的完整 Python 包版本清单，其中本项目的两个可编辑安装项已改为源码包内的相对路径。它用于核对环境，**不是已验证的一键安装脚本**；PyTorch/CUDA、MuJoCo 和其他编译组件仍需按目标机器配置。

## 运行资源

以下文件由使用者从 [TextOp 原作者资源库](https://huggingface.co/datasets/Yochish/TextOp-Data)自行取得，并放入解压后的源码目录：

| 目标路径（相对 `TextOp/`） | 用途 |
| --- | --- |
| `TextOpRobotMDAR/logs/pretrained/checkpoint/ckpt_200000.pth` | DAR 生成模型 |
| `TextOpRobotMDAR/logs/pretrained/checkpoint/vae.pth` | VAE 模型；必须与 DAR 权重同目录 |
| `TextOpRobotMDAR/dataset/PRIVATE-DATA/meanstd.pkl` | 原项目 `USAGE.md` 所述的 checkpoint 配套统计量；当前 `loop_dar` 推理入口不从此处读取 |
| `TextOpRobotMDAR/dataset/PRIVATE-DATA/statistics.yaml` | 原项目数据统计配置；当前无数据加载的推理入口不读取 |
| `TextOpRobotMDAR/dataset/BABEL-AMASS-ROBOT-23dof-FULL-50fps/meanstd.pkl` | 当前推理入口实际读取的归一化统计量 |
| `TextOpRobotMDAR/dataset/BABEL-AMASS-ROBOT-23dof-FULL-50fps/action_statistics.json` | 动作统计量 |
| `TextOpRobotMDAR/description/robots/g1/` | Unitree G1 描述与几何资源；至少需有 `g1_23dof_lock_wrist.xml` 和 `g1_23dof_lock_wrist_fitmotionONLY.xml` 及它们引用的文件 |

`loop_dar` / `loop_dar_pred` 的验证数据配置使用 `data.val.datadir=./dataset/BABEL-AMASS-ROBOT-23dof-FULL-50fps`，因此实际从该目录读取 `meanstd.pkl`。命令中的 `data.datadir=./dataset/PRIVATE-DATA` 不会覆盖 `data.val.datadir`。若要改用另一套归一化统计量，必须显式调整 `data.val.datadir`，并将结果视为不同运行条件。

已核对参考服务器上的关键外部文件；以下哈希可用于判断资源是否与本次验证一致：

| 文件 | SHA256 |
| --- | --- |
| `ckpt_200000.pth` | `9c514d8e61d6f24b9e5b6b278b9987c9d768c7c86883e834f51e0f0c2a18f00f` |
| `vae.pth` | `6522ab17b8904d1ea6a1dcdef241090000706b485312a319007dc4bb3eac8955` |
| `BABEL-AMASS-ROBOT-23dof-FULL-50fps/meanstd.pkl` | `ac5af14f9743773a6e64dc1a2a87251e569e56ea929fa00d6ad750dcb08bd41e` |
| `BABEL-AMASS-ROBOT-23dof-FULL-50fps/action_statistics.json` | `036a432ff3d8d3d790eaaa4f2e65ed0fa05cdb3f7b5fafaf749bb98383438bfc` |
| `g1/g1_23dof_lock_wrist.xml` | `13bde8d8f33546b810b7f3350a6f2b74a43773a293c5d458a53df1807b6eeb8b` |
| `g1/g1_23dof_lock_wrist_fitmotionONLY.xml` | `e1a4260fe73077afd47518417b2d6609148b086438003d1956656ce133ae5101` |

运行前应检查这些资源实际存在、与文档哈希一致，并遵守其各自许可。即使通过配置覆盖 `skeleton.asset.assetRoot`，当前可视化初始化仍会相对工作目录读取 `./description/robots/g1/g1_23dof_lock_wrist.xml`；因此需把完整 G1 资源放在上表位置。交付目录只包含少量已获授权的验证文本，不含 checkpoint、完整训练或基准数据集、训练统计量及机器人描述资源。
