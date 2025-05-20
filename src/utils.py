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
    """Return the value of ``name`` from the environment.

    Parameters
    ----------
    name: str
        Environment variable name.
    default: Any, optional
        Value to return if the variable is missing.  If ``None`` and the
        variable is not set, an :class:`EnvironmentError` is raised.
    resolve_path: bool, optional
        If ``True`` and the value represents a path, resolve it relative to the
        project root.
    """

    if default is None:
        value = os.getenv(name)
        if value is None:
            raise EnvironmentError(
                f"Required environment variable '{name}' is not set and no "
                "default value was provided."
            )
    else:
        value = os.getenv(name, default)

    if value and resolve_path:
        project_root = get_project_root()
        resolved_path = (project_root / value).resolve()
        return str(resolved_path)
    return value
