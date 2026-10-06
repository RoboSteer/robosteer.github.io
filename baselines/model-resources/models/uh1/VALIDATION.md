> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 最小流程验证

2026-10-05 在 <HOST> 的现有 UH-1 环境中，用当前源码工作区和本包样例各运行 1 条。四条均完成 H1 推理、输出重读校验和 H1→G1 SONIC 转换；`summary.json` 均显示 `success=1`、`failed=0`、`unaccounted=0`、`verification.problems=[]`。每条 G1 结果目录都有 6 个 CSV、`metadata.txt`、`info.txt`。

| 任务 | 输入样例 | 导出 H1 帧数 | 筛选前帧数 | G1 转换 |
| --- | --- | ---: | ---: | --- |
| `TXT_GEN` | `L1_TXT_GEN_j7GG8UOpKi0_00002_0_68.txt` | 608 | 608 | 成功 |
| `TXT_FORE` | `L1_TXT_FORE_b9m6sRcFrms_00006_0_108.txt` | 119 | 782 | 成功 |
| `TXT_INTER` | `L1_TXT_INTER_KGqav_-w_qM_00008_665_780.txt` | 95 | 1114 | 成功 |
| `TXT_RETRO` | `L1_TXT_RETRO_Rbj_Jw8PRks_00036_31_140.txt` | 192 | 974 | 成功 |

参考轨迹、SONIC 输出和原始运行记录保存在完整交付目录的 `internal/validation/`，不属于公开资料。`gen_run/`、`fore_run/`、`inter_run/`、`retro_run/` 内含 `run_config.json`、`inputs.jsonl`、`results.jsonl`、`stages.jsonl`、`summary.json` 等；这些内部记录含服务器路径。重跑命令以 [`README_PIPELINES.md`](README_PIPELINES.md) 中的相对路径命令为准。

验证用的是交付时的 <HOST> 源码工作区；内部快照是从同一工作区复制的文件，并可用 `internal/source_manifest.json` 逐文件核对。以上结果证明四条最小流程在现有环境跑通，不代表 40 条样例全部运行、在全新机器部署成功、数值与历史结果一致、动作质量合格或真实机器人可安全执行。
