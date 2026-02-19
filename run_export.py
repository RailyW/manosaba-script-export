from __future__ import annotations

from pathlib import Path

from export_core import run_export
from utils_log import Logger


def main() -> None:
    logger = Logger()
    logger.info("manosaba-script-export 启动")
    logger.info("该工具只会读取游戏目录，不会修改游戏原文件")

    game_root_input = input(
        "请输入游戏根目录（例如 E:\\game\\steam\\steamapps\\common\\manosaba_game）:\n> "
    ).strip().strip('"')

    if not game_root_input:
        logger.error("未输入游戏根目录，程序退出")
        return

    game_root = Path(game_root_input)
    if not game_root.exists() or not game_root.is_dir():
        logger.error(f"路径不存在或不是目录: {game_root}")
        return

    output_input = input(
        "请输入输出目录（留空默认当前目录下 output）:\n> "
    ).strip().strip('"')

    output_dir = Path(output_input) if output_input else Path.cwd() / "output"
    logger.info(f"输出目录: {output_dir}")

    try:
        run_export(game_root=game_root, output_dir=output_dir, logger=logger)
    except Exception as e:
        logger.error(f"执行失败: {e}")


if __name__ == "__main__":
    main()
