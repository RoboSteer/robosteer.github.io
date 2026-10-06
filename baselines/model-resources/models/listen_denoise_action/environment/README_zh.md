# 环境配置

运行平台：Linux x86_64 + NVIDIA GPU。

流水线使用两个 Python 环境：

|环境|Python|PyTorch|用途|
|---|---|---|---|
|LDA|3.9|2.8.0 + cu128，torchvision 0.23.0|音频特征提取、LDA-U 推理|
|GMR|3.10|2.6.0 + cu124|BVH → SMPL-X、G1 重定向、SONIC 导出|

## 使用已有环境

把两个环境的 Python 路径传给运行入口：

```bash
bash scripts/run_audio_to_bvh.sh --lda-python /path/to/lda/bin/python ...
bash scripts/run_bvh_to_robot.sh --gmr-python /path/to/gmr/bin/python ...
bash scripts/run_robot_to_sonic.sh --gmr-python /path/to/gmr/bin/python ...
```

检查解释器和 CUDA：

```bash
/path/to/lda/bin/python -V
/path/to/lda/bin/python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
/path/to/gmr/bin/python -V
/path/to/gmr/bin/python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

## 创建迁移环境

使用 yml 文件创建基础环境，再安装 PyTorch 和依赖：

```bash
conda env create -f environment/lda.yml
conda run -n robosteer-lda python -m pip install \
  torch==2.8.0 torchvision==0.23.0 \
  --index-url https://download.pytorch.org/whl/cu128
conda run -n robosteer-lda python -m pip install \
  -r environment/lda-requirements.txt \
  -c environment/lda-constraints.txt

conda env create -f environment/gmr.yml
conda run -n robosteer-gmr python -m pip install \
  torch==2.6.0 \
  --index-url https://download.pytorch.org/whl/cu124
conda run -n robosteer-gmr python -m pip install \
  -r environment/gmr-requirements.txt \
  -c environment/gmr-constraints.txt
```

`*-requirements.txt` 是直接依赖，`*-constraints.txt` 用于约束传递依赖。GMR 的 SMPL-X 使用固定 commit；运行时通过参数传入 LDA/GMR 代码根目录，不需要重新执行 editable 安装。

## 服务器不能直连 Conda/PyPI

`ProxyCommand` 只代理 SSH 登录。需要访问 Conda、PyPI 或 PyTorch 源时，在本地启动 HTTP 代理并建立 SSH 反向转发：

```bash
# 本地终端
python3 tools/local_http_proxy.py

# 另一个本地终端
ssh -N -R 18080:127.0.0.1:8888 cxt001
```

服务器上设置代理后安装：

```bash
export HTTPS_PROXY=http://127.0.0.1:18080
export HTTP_PROXY=http://127.0.0.1:18080
export ALL_PROXY=http://127.0.0.1:18080
export NO_PROXY=
curl -I https://repo.anaconda.com
conda env create -f environment/lda.yml
```

`tools/local_http_proxy.py` 只监听本地回环地址。安装前请确认服务器具备兼容的 NVIDIA 驱动，并为每个环境使用独立名称或路径。
