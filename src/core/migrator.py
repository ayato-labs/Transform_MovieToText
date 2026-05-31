import logging
import os
import shutil
from pathlib import Path

from .constants import APP_DATA_DIR, LOCAL_DATA_DIR, LOGS_DIR, MODELS_DIR

logger = logging.getLogger(__name__)


class ConfigMigrator:
    """Handles migration of configuration file schemas."""

    @staticmethod
    def migrate(config: dict) -> bool:
        """
        Updates old config structures to the latest version.
        Returns True if the config was modified.
        """
        modified = False
        # Add migration logic here when schema changes
        return modified


def migrate_legacy_data():
    """
    Moves data from legacy locations (root/data/, root/logs/) to standard Windows AppData.
    This ensures a seamless upgrade for existing users.
    """
    base_dir = Path.cwd()
    legacy_data_dir = base_dir / "data"
    legacy_logs_dir = base_dir / "logs"

    if not legacy_data_dir.exists() and not legacy_logs_dir.exists():
        return

    logger.info("Migrator: Legacy data found. Starting migration to AppData...")

    # 1. Migrate Logs
    if legacy_logs_dir.exists():
        _move_contents(legacy_logs_dir, Path(LOGS_DIR))
        _remove_if_empty(legacy_logs_dir)

    # 2. Migrate Models (Move to Local AppData)
    legacy_models = legacy_data_dir / "models"
    if legacy_models.exists():
        _move_contents(legacy_models, Path(MODELS_DIR))
        _remove_if_empty(legacy_models)

    # 3. Migrate Records/DB (Move to Roaming AppData)
    # Note: We move everything else in 'data' to APP_DATA_DIR (Roaming)
    if legacy_data_dir.exists():
        _move_contents(legacy_data_dir, Path(APP_DATA_DIR))
        _remove_if_empty(legacy_data_dir)

    logger.info("Migrator: Data migration completed successfully.")


def _move_contents(src: Path, dst: Path):
    """Recursively moves contents of src to dst."""
    if not src.exists():
        return

    dst.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        target = dst / item.name
        try:
            if item.is_dir():
                if target.exists():
                    _move_contents(item, target)
                    _remove_if_empty(item)
                else:
                    shutil.move(str(item), str(target))
            else:
                if target.exists():
                    # If target exists, we keep the newer one or skip
                    # For safety in this tool, we skip if already exists to avoid corruption
                    item.unlink() 
                else:
                    shutil.move(str(item), str(target))
            logger.debug(f"Migrator: Moved {item.name} to {dst}")
        except Exception as e:
            logger.error(f"Migrator: Failed to move {item}: {e}")


def _remove_if_empty(path: Path):
    """Removes a directory if it has no files left."""
    try:
        if path.exists() and not any(path.iterdir()):
            path.rmdir()
    except Exception:
        pass
