from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Dict, List

from parsers import DialogueRecord, build_speaker_mapping, export_voice_bundle, parse_localized_script_bundle
from utils_log import Logger


def _find_asset_root(game_root: Path) -> Path:
    return game_root / "manosaba_Data" / "StreamingAssets" / "aa" / "StandaloneWindows64"


def _collect_bundles(asset_root: Path, logger: Logger) -> tuple[List[Path], List[Path], Path]:
    bundles = sorted(asset_root.glob("*.bundle"))
    logger.info(f"[SCAN] 在 {asset_root} 发现 bundle: {len(bundles)}")

    text_bundles = [p for p in bundles if "general-localization-zhhans-scripts-" in p.name]
    voice_bundles = [p for p in bundles if "general-voice-" in p.name]
    char_name_bundle = asset_root / "general-localization-zhhans-text_assets_all.bundle"

    logger.info(f"[SCAN] 文本 bundle 数量: {len(text_bundles)}")
    logger.info(f"[SCAN] 语音 bundle 数量: {len(voice_bundles)}")
    logger.info(f"[SCAN] 角色名映射 bundle: {char_name_bundle}")
    return text_bundles, voice_bundles, char_name_bundle


def _write_csv(records: List[DialogueRecord], csv_path: Path, logger: Logger) -> None:
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["line_id", "speaker_ja", "speaker_zh", "line_ja", "line_zh", "voice_file"],
        )
        writer.writeheader()
        for rec in records:
            writer.writerow(
                {
                    "line_id": rec.line_id,
                    "speaker_ja": rec.speaker_ja,
                    "speaker_zh": rec.speaker_zh,
                    "line_ja": rec.line_ja,
                    "line_zh": rec.line_zh,
                    "voice_file": rec.voice_file,
                }
            )
    logger.info(f"[CSV] 已写入: {csv_path}")


def run_export(game_root: Path, output_dir: Path, logger: Logger) -> None:
    start = time.time()

    asset_root = _find_asset_root(game_root)
    if not asset_root.exists():
        raise FileNotFoundError(f"未找到资源目录: {asset_root}")

    output_dir.mkdir(parents=True, exist_ok=True)
    voices_dir = output_dir / "voices"
    voices_dir.mkdir(parents=True, exist_ok=True)

    text_bundles, voice_bundles, char_name_bundle = _collect_bundles(asset_root, logger)

    speaker_map: Dict[str, str] = {}
    if char_name_bundle.exists():
        speaker_map = build_speaker_mapping(char_name_bundle, logger)
    else:
        logger.warn("[MAP] 未找到角色名映射 bundle，speaker_zh 可能回退为 speaker_ja")

    all_records: List[DialogueRecord] = []
    for i, bundle in enumerate(text_bundles, 1):
        logger.progress("TEXT", i, len(text_bundles), f"读取 {bundle.name}")
        try:
            recs = parse_localized_script_bundle(bundle, speaker_map, logger)
            all_records.extend(recs)
            logger.info(f"[TEXT] {bundle.name} 新增 {len(recs)} 条，累计 {len(all_records)}")
        except Exception as e:
            logger.error(f"[TEXT] 处理失败: {bundle.name} | {e}")

    voice_map: Dict[str, str] = {}
    for i, bundle in enumerate(voice_bundles, 1):
        logger.progress("VOICE", i, len(voice_bundles), f"读取 {bundle.name}")
        try:
            sub_map = export_voice_bundle(bundle, voices_dir, logger)
            for k, v in sub_map.items():
                if k not in voice_map:
                    voice_map[k] = v
        except Exception as e:
            logger.error(f"[VOICE] 处理失败: {bundle.name} | {e}")

    matched = 0
    missing_voice = 0
    missing_speaker_map = 0
    for rec in all_records:
        rec.voice_file = voice_map.get(rec.line_id, "")
        if rec.voice_file:
            matched += 1
        else:
            missing_voice += 1
        if rec.speaker_ja and rec.speaker_zh == rec.speaker_ja:
            missing_speaker_map += 1

    csv_path = output_dir / "dialogue.csv"
    _write_csv(all_records, csv_path, logger)

    elapsed = time.time() - start
    logger.info("[DONE] 导出完成")
    logger.info(f"[DONE] 文本总条数: {len(all_records)}")
    logger.info(f"[DONE] 语音映射总数: {len(voice_map)}")
    logger.info(f"[DONE] 成功匹配语音: {matched}")
    logger.warn(f"[DONE] 缺失语音条数: {missing_voice}")
    logger.warn(f"[DONE] 未映射中文名条数: {missing_speaker_map}")
    logger.info(f"[DONE] CSV: {csv_path}")
    logger.info(f"[DONE] Voices目录: {voices_dir}")
    logger.info(f"[DONE] 总耗时: {elapsed:.2f}s")
