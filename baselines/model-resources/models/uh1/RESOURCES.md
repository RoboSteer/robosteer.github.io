> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 外部资源与放置路径

| 资源 | 用途 | 获取位置 | 本包状态 |
| --- | --- | --- | --- |
| `UH1_Action_Tokenizer.pth` | H1 动作 tokenizer | [UH-1 原作者模型页](https://huggingface.co/USC-GVL/UH-1) | 仅链接，自行下载 |
| `UH1_Transformer.pth` | 文本条件 Transformer | 同上 | 仅链接，自行下载 |
| `Mean.npy`、`Std.npy` | H1 动作反标准化 | 同一原作者资源 / 内部源码快照 | 内部快照有文件；公开资料仅说明来源 |
| CLIP `ViT-B/32` | 文本编码 | [OpenAI CLIP](https://github.com/openai/CLIP) 自动下载或预缓存 | 不提供模型缓存 |
| GMR `general_motion_retargeting` | G1 正向运动学 | [YanjieZe/GMR](https://github.com/YanjieZe/GMR) | 不在包内；已核对服务器快照 commit `bb1bbe40774794fceb2a7c579a3464a28e68c844` |
| G1 `g1_29dof.xml` 与 `meshes/` | G1 关节范围和运动学 | [NVlabs/GR00T-WholeBodyControl](https://github.com/NVlabs/GR00T-WholeBodyControl) 的 `gear_sonic_deploy/g1/` | 不在包内；已核对服务器快照 commit `3d3e593369bc1384a8f5d1f22830bf20cb3a6047` |

推理脚本在 `UH-1/`、`UH-1/checkpoints/UH-1/`、`UH-1/checkpoints/` 中按顺序查找 **四个同目录** 文件。内部快照自带小型 `Mean.npy`、`Std.npy`，可将两个 `.pth` 放在 `UH-1/` 根目录。公开使用者须自行取得四个文件，并核对来源及许可。

转换器的当前路径约定是：与 `UH-1/` 同级放置 `GMR/` 和 `GR00T-WholeBodyControl/`，即：

```text
source/
  UH-1/
  GMR/general_motion_retargeting/{kinematics_model.py,torch_utils.py}
  GR00T-WholeBodyControl/gear_sonic_deploy/g1/{g1_29dof.xml,meshes/...}
```

从对应官方仓库自行取得资源并放到上述位置。转换器能在 GMR 顶层导入失败时，直接加载同级 `GMR` 的两个运动学模块。G1 XML 引用 `meshes/`，不要只复制 XML。转换前先检查上述路径均存在，再执行 `python scripts/convert_h1_to_g1_sonic.py --help`。外部资源有各自许可证；保留随仓库提供的许可证和声明。
