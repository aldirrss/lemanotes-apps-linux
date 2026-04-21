import json
from pathlib import Path

_CONFIG_DIR  = Path.home() / ".config" / "lemanotes"
_CONFIG_FILE = _CONFIG_DIR / "settings.json"
_DEFAULTS    = {
    "theme": "dark", "font_size": 15, "disabled_shortcuts": [],
    "note_sort": "updated_desc", "notebook_sort": "name_asc",
    "filter_pinned": False, "notebook_order": [],
}


def load_settings() -> dict:
    try:
        if _CONFIG_FILE.exists():
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**_DEFAULTS, **json.load(f)}
    except Exception:
        pass
    return dict(_DEFAULTS)


def save_settings(settings: dict):
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
