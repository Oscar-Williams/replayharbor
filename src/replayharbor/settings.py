"""Explicit .env loading without exporting credentials to subprocesses."""
import os
import re
from pathlib import Path
from dotenv import dotenv_values


class Settings:
    __slots__ = ("_key", "base_url", "model")

    def __init__(self, key, base_url, model):
        if base_url not in {"https://api.deepseek.com", "https://api.deepseek.com/v1"}:
            raise ValueError("DeepSeek endpoint must be an approved official HTTPS URL")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", model):
            raise ValueError("invalid model identifier")
        if key and (not re.fullmatch(r"sk-[A-Za-z0-9_-]{20,200}", key)):
            raise ValueError("invalid credential format; check the local .env file")
        self._key, self.base_url, self.model = key, base_url, model

    def __repr__(self):
        return f"Settings(base_url={self.base_url!r}, model={self.model!r}, credential_present={bool(self._key)})"

    def public_summary(self):
        return dict(provider="deepseek", base_url=self.base_url, model=self.model,
                    credential_present=bool(self._key), network_checked=False)

    def auth_headers(self):
        """Use only at the HTTP boundary; never persist or log these headers."""
        if not self._key:
            raise ValueError("DEEPSEEK_API_KEY is missing; configure it locally")
        return {"Authorization": "Bearer " + self._key}


def load_settings(project_root, environ=None):
    root = Path(project_root).resolve()
    path = root / ".env"
    if path.is_symlink():
        raise ValueError(".env must be a local regular file")
    # Explicit path prevents accidental loading of another project's credentials.
    values = dotenv_values(path, interpolate=False, encoding="utf-8-sig") if path.exists() else {}
    env = os.environ if environ is None else environ
    def get(name, default=""):
        return env.get(name, values.get(name) or default).strip()
    return Settings(get("DEEPSEEK_API_KEY"),
                    get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                    get("DEEPSEEK_MODEL", "deepseek-flash"))
