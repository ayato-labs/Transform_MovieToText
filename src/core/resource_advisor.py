import logging

import psutil

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)


class ResourceAdvisor:
    """
    Analyzes system resources (RAM/VRAM) to recommend optimal AI models.
    """

    # Static Golden Rules for 2026 hardware
    TIER_MAPPING = {
        "Entry": {"min_ram": 8, "min_vram": 0, "whisper": "base", "ollama": "llama3.2:1b-instruct-q4_K_M"},
        "SmallGPU": {"min_ram": 8, "min_vram": 4, "whisper": "small", "ollama": "phi3.5:3.8b-mini-instruct-q4_K_M"},
        "Standard": {"min_ram": 16, "min_vram": 8, "whisper": "medium", "ollama": "llama3.1:8b-instruct-q4_K_M"},
        "Pro": {"min_ram": 32, "min_vram": 10, "whisper": "large-v3", "ollama": "gemma2:9b-instruct-q4_K_M"},
        "Monster": {"min_ram": 64, "min_vram": 22, "whisper": "large-v3", "ollama": "llama3.3:70b-instruct-q4_K_M"},
    }

    @classmethod
    def get_system_specs(cls):
        """Detects total RAM and VRAM (if GPU available)."""
        ram_info = psutil.virtual_memory()
        total_ram = round(ram_info.total / (1024**3), 1)

        total_vram = 0.0
        if HAS_TORCH and torch.cuda.is_available():
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            total_vram = round(vram_bytes / (1024**3), 1)

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
