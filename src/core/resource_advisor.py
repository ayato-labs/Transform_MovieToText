import logging
import subprocess

import psutil

logger = logging.getLogger(__name__)


class ResourceAdvisor:
    """
    Analyzes system resources (RAM/VRAM) to recommend optimal AI models.
    """

    # Static Golden Rules for 2026 hardware (Prioritizing gemma4:e2b for stability)
    TIER_MAPPING = {
        "Entry": {"min_ram": 8, "min_vram": 0, "whisper": "base", "ollama": "gemma4:e2b"},
        "SmallGPU": {"min_ram": 8, "min_vram": 4, "whisper": "small", "ollama": "gemma4:e2b"},
        "Standard": {"min_ram": 16, "min_vram": 8, "whisper": "medium", "ollama": "gemma4:e2b"},
        "Pro": {"min_ram": 32, "min_vram": 10, "whisper": "large-v3", "ollama": "gemma4:e2b"},
        "Monster": {"min_ram": 64, "min_vram": 22, "whisper": "large-v3", "ollama": "gemma4:e2b"},
    }

    @classmethod
    def get_system_specs(cls):
        """Detects total RAM and VRAM (if GPU available)."""
        ram_info = psutil.virtual_memory()
        total_ram = round(ram_info.total / (1024**3), 1)

        total_vram = 0.0
        try:
            # Run nvidia-smi to get total VRAM in MiB
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2
            )
            # Take the first GPU's memory
            vram_mb = int(result.stdout.strip().split('\n')[0])
            total_vram = round(vram_mb / 1024.0, 1)
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError, IndexError) as e:
            logger.warning(f"ResourceAdvisor: Failed to detect VRAM, defaulting to 0: {e}")

        return total_ram, total_vram

    @classmethod
    def get_best_match(cls):
        """Returns the recommended model set based on detected hardware."""
        ram, vram = cls.get_system_specs()
        logger.info(f"ResourceAdvisor: Detected specs -> RAM: {ram}GB, VRAM: {vram}GB")

        # Priority mapping from Monster down to Entry
        if ram >= 64 and vram >= 22:
            tier_key = "Monster"
        elif ram >= 32 and vram >= 10:
            tier_key = "Pro"
        elif ram >= 16 and vram >= 8:
            tier_key = "Standard"
        elif ram >= 8 and vram >= 4:
            tier_key = "SmallGPU"
        else:
            tier_key = "Entry"

        config = cls.TIER_MAPPING[tier_key]
        logger.info(f"ResourceAdvisor: Mapped to Tier '{tier_key}'. (Whisper: {config['whisper']}, Ollama: {config['ollama']})")
        return {"tier": tier_key, "whisper": config["whisper"], "ollama": config["ollama"], "ram": ram, "vram": vram}
