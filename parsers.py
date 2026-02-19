from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import UnityPy

from utils_log import Logger


@dataclass
class DialogueRecord:
    line_id: str
    speaker_ja: str
    speaker_zh: str
    line_ja: str
    line_zh: str
    voice_file: str


def _decode_text_asset_script(script_obj) -> str:
    data = getattr(script_obj, "m_Script", b"")
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)


def _speaker_from_line_id(line_id: str) -> str:
    if "_" not in line_id:
        return ""
    tail = line_id.split("_", 1)[1]
    # e.g. Leia001 -> Leia, EmaFake001 -> EmaFake
    m = re.match(r"^([A-Za-z][A-Za-z0-9_]*?)(\d+)?$", tail)
    return m.group(1) if m else tail


def _normalize_speaker_key(name: str) -> List[str]:
    candidates = [name]
    if name.startswith("Creature") and len(name) > len("Creature"):
        candidates.append(name[len("Creature") :])
    # 一些名字可能包含空白
    candidates.append(name.strip())
    dedup = []
    seen = set()
    for x in candidates:
        if x and x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup


def build_speaker_mapping(text_bundle_path: Path, logger: Logger) -> Dict[str, str]:
    logger.info(f"[MAP] 读取角色映射 bundle: {text_bundle_path}")
    mapping: Dict[str, str] = {}

    env = UnityPy.load(str(text_bundle_path))
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        name = getattr(data, "m_Name", "")
        if name != "CharacterNames":
            continue

        raw = _decode_text_asset_script(data)
        for line in raw.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k and v:
                mapping[k] = v
        break

    logger.info(f"[MAP] 角色映射条数: {len(mapping)}")
    return mapping


def parse_localized_script_bundle(
    bundle_path: Path,
    speaker_map: Dict[str, str],
    logger: Logger,
) -> List[DialogueRecord]:
    records: List[DialogueRecord] = []

    env = UnityPy.load(str(bundle_path))

    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        script_name = getattr(data, "m_Name", "")
        content = _decode_text_asset_script(data)
        lines = content.splitlines()

        current_line_id: Optional[str] = None
        current_speaker_ja: str = ""
        ja_lines: List[str] = []
        zh_lines: List[str] = []

        def flush_current() -> None:
            nonlocal current_line_id, current_speaker_ja, ja_lines, zh_lines
            if not current_line_id:
                return

            speaker_ja = current_speaker_ja or _speaker_from_line_id(current_line_id)
            speaker_zh = ""
            for key in _normalize_speaker_key(speaker_ja):
                if key in speaker_map:
                    speaker_zh = speaker_map[key]
                    break
            if not speaker_zh:
                speaker_zh = speaker_ja

            rec = DialogueRecord(
                line_id=current_line_id,
                speaker_ja=speaker_ja,
                speaker_zh=speaker_zh,
                line_ja="\n".join(x for x in ja_lines if x).strip(),
                line_zh="\n".join(x for x in zh_lines if x).strip(),
                voice_file="",
            )
            records.append(rec)

            current_line_id = None
            current_speaker_ja = ""
            ja_lines = []
            zh_lines = []

        for line in lines:
            if line.startswith("# "):
                flush_current()
                current_line_id = line[2:].strip()
                continue

            if current_line_id is None:
                continue

            if line.startswith("; > "):
                # 示例: ; > Leia: |#0101Trial00_Leia001|
                text = line[4:].strip()
                if ":" in text:
                    maybe_name = text.split(":", 1)[0].strip()
                    if maybe_name and not maybe_name.startswith("@"):
                        current_speaker_ja = maybe_name
                continue

            if line.startswith(";"):
                # 日文行（去掉 ';' 前缀）
                ja = line[1:].lstrip()
                if ja and not ja.startswith("日本語 <ja>"):
                    ja_lines.append(ja)
                continue

            # 中文行（非注释、非分段标记）
            if line.strip():
                zh_lines.append(line.rstrip())

        flush_current()
        logger.info(f"[TEXT] TextAsset={script_name} 解析得到 {len(records)} 条(累计)")

    return records


def export_voice_bundle(
    bundle_path: Path,
    voices_output_dir: Path,
    logger: Logger,
) -> Dict[str, str]:
    line_to_voice: Dict[str, str] = {}
    env = UnityPy.load(str(bundle_path))

    clip_count = 0
    written_count = 0

    for obj in env.objects:
        if obj.type.name != "AudioClip":
            continue

        clip = obj.read()
        clip_name = getattr(clip, "m_Name", "")
        samples = getattr(clip, "samples", {})

        if not isinstance(samples, dict) or not samples:
            continue

        clip_count += 1

        for file_name, audio_bytes in samples.items():
            out_path = voices_output_dir / file_name
            if not out_path.exists():
                out_path.write_bytes(audio_bytes)
                written_count += 1

            if clip_name and clip_name not in line_to_voice:
                line_to_voice[clip_name] = file_name

        if clip_count % 300 == 0:
            logger.info(
                f"[VOICE] {bundle_path.name} 已处理 AudioClip {clip_count}，当前导出文件 {written_count}"
            )

    logger.info(
        f"[VOICE] {bundle_path.name} 完成：AudioClip={clip_count}, 新写入语音文件={written_count}, 映射条数={len(line_to_voice)}"
    )

    return line_to_voice
