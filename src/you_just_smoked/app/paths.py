from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "you-just-smoked"


@dataclass(frozen=True, slots=True)
class AppPaths:
    config_file: Path
    database: Path
    models: Path
    log_file: Path

    @classmethod
    def default(cls) -> AppPaths:
        dirs = PlatformDirs(APP_NAME, appauthor=False)
        return cls(
            config_file=Path(dirs.user_config_dir) / "config.toml",
            database=Path(dirs.user_data_dir) / "episodes.sqlite3",
            models=Path(dirs.user_cache_dir) / "models",
            log_file=Path(dirs.user_log_dir) / "you-just-smoked.log",
        )
