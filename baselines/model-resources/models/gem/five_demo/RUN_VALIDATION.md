> **历史验证记录：** 对应上游源码不在当前公开包内；自建输入的参考结果仍保留。见 [公开范围](../PUBLIC_SCOPE.md)。

# 五个 demo 脚本副本：运行验证

本表检查原独立副本的已验证模型中间结果；新运行写入 outputs/，参考结果保存在 reference_outputs/；路径均相对于本包根目录。`smpl_params.pt` 是五个入口的主要输出。

| 入口 | 预期 | 已生成 |
| --- | ---: | ---: |
| `demo_smpl.py` | 5 | 5 |
| `demo_smpl_text_batch.py` | 30 | 30 |
| `demo_smpl_hpe.py` | 5 | 5 |
| `demo_smpl_predict_batch.py` | 30 | 30 |
| `demo_smpl_interleaved_batch.py` | 5 | 5 |

另有 `reference_outputs/text_batch/TXT_GEN/` 的单类命令参考结果 5 个。`reference_outputs/text_pred_generated/` 保存 TXT_FORE、TXT_INTER、TXT_RETRO 各 5 个筛选后的生成段结果；因此包内共有 80 个完整序列结果和 15 个文本预测生成段结果，共 95 个 `smpl_params.pt`。后者由原始文本批量结果按目标指令的 `segment_info` 截取，单个文件只保留一段 100 帧文本生成动作。

`SOURCE_MANIFEST.tsv`：155 个文件副本，校验失败 0 个。
视频预测失败记录：0 条。
交替批量状态：5 条，其中成功 5 条。

- `demo_smpl.py` 样例 `reference_outputs/demo_smpl/MIXED_01/clip_mix/smpl_params.pt`：87344 字节；片段类型 video, text。
- `demo_smpl_text_batch.py` 样例 `reference_outputs/text_batch_all/TXT_GEN/TXT_GEN_01/smpl_params.pt`：69872 字节；片段类型 text。
- `demo_smpl_hpe.py` 样例 `reference_outputs/video_hpe/video_01/smpl_params.pt`：20336 字节；片段类型 无 segment_info（HPE）。
- `demo_smpl_predict_batch.py` 样例 `reference_outputs/video_predict_all/VID_RETRO_HUMAN/human01/smpl_params.pt`：87344 字节；片段类型 text, video。
- `demo_smpl_interleaved_batch.py` 样例 `reference_outputs/interleaved/MIXED_01/smpl_params.pt`：87344 字节；片段类型 video, text。

样例视频为现存关键帧静态视频，验证输入格式和运行流程，不代表正式 VID 预测质量。

## GMR 与 SONIC 后处理

上述 95 个参考 `smpl_params.pt` 均已转换为 `reference_postprocess/gmr/<原相对任务路径>/smplx_motion.npz` 和 `robot_motion.pkl`，并在 `reference_postprocess/sonic/<原相对任务路径>/` 各生成 6 个 CSV、`metadata.txt` 和 `info.txt`。SMPL-X、G1 PKL、SONIC 目录均为 95/95；逐文件形状、帧数和有限值检查为 95/95。文本预测若只需目标生成段，应使用 `text_pred_generated/` 对应的后处理结果；`text_batch_all/TXT_FORE/INTER/RETRO` 保留完整条件与生成序列供对照。推荐正式任务共 75 条，选择规则见 [后处理教程](../POSTPROCESS.md)。
