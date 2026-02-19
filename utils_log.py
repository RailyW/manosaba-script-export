from __future__ import annotations

from datetime import datetime


class Logger:
    def _ts(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def info(self, message: str) -> None:
        print(f"[{self._ts()}] [INFO] {message}")

    def warn(self, message: str) -> None:
        print(f"[{self._ts()}] [WARN] {message}")

    def error(self, message: str) -> None:
        print(f"[{self._ts()}] [ERROR] {message}")

    def progress(self, stage: str, current: int, total: int, extra: str = "") -> None:
        pct = (current / total * 100) if total else 0
        suffix = f" | {extra}" if extra else ""
        print(f"[{self._ts()}] [{stage}] {current}/{total} ({pct:.1f}%){suffix}")
