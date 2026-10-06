# 最小资源清单

这是公开交付包的外部资源说明，不是资源下载包。当前目录中的每一项均为 `included=false`；清单中的路径是上游相对路径，链接用于获取和核对来源，不表示 RoboSteer 已获得再分发权。

资源分组见 resources.yaml；96 个具体文件的相对路径、字节数、SHA-256 与来源位置见 resource_files.json。所有 included=false；未复制大型或受限资源。

## 默认 LDA-U 链必需

1. dance_LDA-U.ckpt：Zenodo 8156769/v1。dance_LDA.ckpt 只作可选盘点。
2. ch0_spec_beatact_features.txt：通过权重 ZIP 内 pickle 指令字符串静态检查及源码确认；三列为 Chroma_0、Spectralflux_0、Beatactivation_0。
3. data_pipe.expmap_30fps.sav：utils.logging_mixin 用于将预测特征反变换为 BVH。
4. 十个 motorica_dance/*.audio29_30fps.pkl：作为候选固定参考范围；实际读取 Beatactivation_0 范围，不需要同目录原始音乐。历史输入目录若有其他参考文件，结果可能不同。
5. GMR/assets/body_models/smplx/SMPLX_NEUTRAL.pkl：当前 neutral 默认链；从 SMPL-X 官方自行获取。官方具体资源发布版本待确认，已固定本地文件哈希。
6. GMR/general_motion_retargeting/ik_configs/smplx_to_g1.json。
7. GMR/assets/unitree_g1/g1_mocap_29dof.xml 和其 mesh：MuJoCo 重定向/贴地使用。
8. GR00T 的 gear_sonic_deploy/g1/g1_29dof.xml：SONIC 导出中的 GMR KinematicsModel 读取 XML 骨架；当前解析器不加载 mesh。相关 mesh 仍列入完整资产审计，标为非本链最小必需。

其他 txt 元数据列为候选/可选，不能要求用户全部下载；LDA（非 U）和风格条件模式应另行核对。

## 获取与许可

固定源码版本的原始资源可由用户从官方仓库取得；清单记录的是对应上游位置和准备环境中的文件哈希，尚未逐一从公网下载比对。下载后应校验，不匹配时不能宣称同一资源。`sha256` 为空的多文件资源仍需按 `resource_files.json` 逐文件核对。
LDA 上游许可限制研究用途与未经授权再分发；权重与元数据默认外链。SMPL-X 单独获取。GMR 代码 MIT、GMR 的 G1 资产目录 BSD-3-Clause；SONIC 资产的单独来源和许可范围待确认。
样例音频尚未选定，不打包历史音乐。此清单不包含控制器权重，也不声称提供训练/完整评测数据。

适配层采用包根目录的 MIT License；上传前仍需再次核对 SONIC/G1 资产的来源条款。公开包的验证摘要见 [../validation/report.md](../validation/report.md)；完整日志和生成文件保留在内部准备目录，不随本目录上传。
