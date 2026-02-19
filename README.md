# manosaba-script-export

用于从魔法少女的魔女审判中提取剧情文本与语音，并导出为：

- `output/dialogue.csv`
- `output/voices/*.wav`

## 依赖

```bash
pip install UnityPy
```

## 用法

```bash
python run_export.py
```

按提示输入：
1. 游戏根目录
2. 输出目录（可留空，默认当前目录 `output`）

## 输出字段

`dialogue.csv` 字段：

- `line_id`
- `speaker_ja`
- `speaker_zh`
- `line_ja`
- `line_zh`
- `voice_file`

## 脚本文件说明

- `run_export.py`：入口与交互
- `export_core.py`：流程编排
- `parsers.py`：文本/语音解析逻辑
- `utils_log.py`：日志工具
