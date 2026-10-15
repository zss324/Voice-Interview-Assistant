from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv
import win32crypt

BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "deepseek-ai/DeepSeek-V4-Flash"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


load_dotenv(app_dir() / ".env")


@dataclass
class Profile:
    job_title: str = ""
    company: str = ""
    job_description: str = ""
    resume_file: str = ""
    resume_text: str = ""
    opacity: int = 90
    hide_taskbar: bool = True


class Config:
    def __init__(self) -> None:
        self.path = app_dir() / "profile.json"
        self.key_path = app_dir() / "api_key.dat"
        self.profile = self._load()

    def _load(self) -> Profile:
        if not self.path.exists():
            return Profile()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            values = {key: raw[key] for key in Profile.__dataclass_fields__ if key in raw}
            profile = Profile(**values)
            profile.opacity = max(35, min(100, int(profile.opacity)))
            return profile
        except (OSError, ValueError, TypeError):
            return Profile()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(self.profile), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def clear(self) -> None:
        self.profile = Profile()
        self.save()
        self.key_path.unlink(missing_ok=True)

    def api_key(self) -> str:
        if self.key_path.exists():
            try:
                encrypted = self.key_path.read_bytes()
                return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode("utf-8")
            except (OSError, ValueError, UnicodeError):
                return ""
        return os.environ.get("INTERVIEW_API_KEY", "").strip()

    def save_api_key(self, key: str) -> None:
        key = key.strip()
        if not key:
            self.key_path.unlink(missing_ok=True)
            return
        encrypted = win32crypt.CryptProtectData(key.encode("utf-8"), "InterviewAI", None, None, None, 0)
        temporary = self.key_path.with_suffix(".tmp")
        temporary.write_bytes(encrypted)
        temporary.replace(self.key_path)
