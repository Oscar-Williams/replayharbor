"""Reject credential-bearing exports before creating any files."""
import re

TOKEN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")
SENSITIVE_FIELDS = {"authorization", "api_key", "deepseek_api_key", "openai_api_key", "access_token", "secret"}


def assert_publishable(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_FIELDS:
                raise ValueError("export rejected: credential field detected")
            assert_publishable(str(key))
            assert_publishable(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            assert_publishable(item)
    elif isinstance(value, str) and TOKEN.search(value):
        raise ValueError("export rejected: credential pattern detected")
