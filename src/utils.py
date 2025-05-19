import logging
import os
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


def get_project_root() -> Path:
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / ".env").exists():
            return parent
    return current_path


def get_env_variable(name: str, default=None, resolve_path=False) -> str:
    value = os.getenv(name, default)
    if value and resolve_path:
        project_root = get_project_root()
        resolved_path = (project_root / value).resolve()
        return str(resolved_path)
    return value
