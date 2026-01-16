# mypy: warn_unused_ignores=False
import sys
from pathlib import Path
from typing import Any, cast

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore

from .settings import Settings


def _deep_update(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively update a dictionary."""
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _load_toml(path: Path) -> dict[str, Any]:
    """Load and parse a TOML file if it exists."""
    if not path.exists():
        return {}

    with open(path, "rb") as f:
        data: Any = tomllib.load(f)
        return cast(dict[str, Any], data)


async def load_config(
    user_config_path: Path | None = None,
    project_config_path: Path | None = None,
) -> Settings:
    """Load and merge configuration from multiple sources.

    Priority (highest to lowest):
    1. Project config (.pygent/config.toml)
    2. User config (~/.config/pygent/config.toml)
    3. Defaults

    Args:
        user_config_path: Override user config location.
        project_config_path: Override project config location.

    Returns:
        Merged Settings instance.
    """
    # 1. Start with defaults (via Settings instantiation)
    # We load dicts first, then merge, then validate with Pydantic

    # Defaults are implicit in the empty dict base for Pydantic,
    # but to merge correctly we should probably load them layer by layer into a dict.

    # Actually, Pydantic models are best created from the final merged dict.
    config_data: dict[str, Any] = {}

    # 2. User Config
    if user_config_path is None:
        user_config_path = Path.home() / ".config" / "pygent" / "config.toml"

    user_config = _load_toml(user_config_path)
    config_data = _deep_update(config_data, user_config)

    # 3. Project Config
    if project_config_path is None:
        project_config_path = Path.cwd() / ".pygent" / "config.toml"

    project_config = _load_toml(project_config_path)
    config_data = _deep_update(config_data, project_config)

    # 4. Create Settings (this handles validation and defaults for missing keys)
    return Settings(**config_data)
