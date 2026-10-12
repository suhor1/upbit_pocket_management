"""API Key 등 실행에 필요한 설정값 로딩."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError

DEFAULT_ENV_FILE = ".env"


def _load_dotenv(path: Path) -> None:
    """간단한 .env 로더. python-dotenv가 없어도 동작한다."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    access_key: str
    secret_key: str
    base_url: str = "https://api.upbit.com"

    @classmethod
    def load(cls, env_file: str | os.PathLike[str] = DEFAULT_ENV_FILE) -> "Settings":
        _load_dotenv(Path(env_file))

        access_key = os.environ.get("UPBIT_OPEN_API_ACCESS_KEY", "").strip()
        secret_key = os.environ.get("UPBIT_OPEN_API_SECRET_KEY", "").strip()

        if not access_key or not secret_key:
            raise ConfigError(
                "API Key가 설정되어 있지 않습니다.\n"
                "UPBIT_OPEN_API_ACCESS_KEY / UPBIT_OPEN_API_SECRET_KEY 환경변수를\n"
                f"지정하거나, 프로젝트 루트의 {env_file} 파일에 아래 형식으로 적어주세요.\n"
                "  UPBIT_OPEN_API_ACCESS_KEY=...\n"
                "  UPBIT_OPEN_API_SECRET_KEY=...\n"
                "※ 메인포켓에서 발급된 Key에 [포켓관리] 권한이 있어야 합니다."
            )

        base_url = os.environ.get("UPBIT_BASE_URL", cls.base_url).strip()
        return cls(access_key=access_key, secret_key=secret_key, base_url=base_url.rstrip("/"))
