from pathlib import Path

from pydantic import BaseModel

from lazyft import paths


class LftSettings(BaseModel):
    base_config_path: Path = None

    def save(self):
        paths.LAZYFT_SETTINGS_PATH.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls):
        if paths.LAZYFT_SETTINGS_PATH.exists():
            return cls.model_validate_json(paths.LAZYFT_SETTINGS_PATH.read_text())
        else:
            return cls()
