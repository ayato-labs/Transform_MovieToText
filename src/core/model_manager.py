"""
ModelManager: Handles lazy loading, verification, and storage of AI models.
"""

import os
import requests
import hashlib
import tarfile
from loguru import logger
from tqdm import tqdm

class ModelManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.registered_clients = {}
        
        # Manifest of models to download
        self.models = {
            "pyannote-segmentation-3.0": {
                "type": "archive",
                "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2",
                "expected_file": "sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
            },
            "cam++_voxceleb_common.onnx": {
                "type": "file",
                "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx",
                "expected_file": "cam++_voxceleb_common.onnx"
            }
        }

    def register(self, client_name, client_instance):
        """Registers a client for VRAM management."""
        self.registered_clients[client_name] = client_instance
        logger.info(f"ModelManager: Registered client '{client_name}'")

    def request_vram(self, client_name):
        """Placeholder for VRAM request logic."""
        logger.info(f"ModelManager: VRAM requested by '{client_name}'")

    def _calculate_sha256(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def download_model(self, model_key):
        model_info = self.models.get(model_key)
        if not model_info:
            logger.error(f"Model {model_key} not in manifest.")
            return False
            
        url = model_info["url"]
        is_archive = model_info.get("type") == "archive"
        
        # Determine download target path
        file_name = url.split('/')[-1]
        download_path = os.path.join(self.base_dir, file_name)
        
        logger.info(f"Downloading {file_name} from GitHub...")
        response = requests.get(url, stream=True, allow_redirects=True)
        if response.status_code != 200:
             logger.error(f"Failed to download {url}. HTTP {response.status_code}")
             return False

        total_size = int(response.headers.get('content-length', 0))
        
        with open(download_path, "wb") as f, tqdm(
            desc=file_name,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                f.write(data)
                bar.update(len(data))
        
        if is_archive:
            logger.info(f"Extracting {file_name}...")
            try:
                with tarfile.open(download_path, "r:bz2") as tar:
                    tar.extractall(path=self.base_dir)
                os.remove(download_path)  # Clean up archive
                logger.info(f"Extraction complete.")
            except Exception as e:
                logger.error(f"Failed to extract {file_name}: {e}")
                return False

        return True

    def ensure_models(self):
        for model_key, info in self.models.items():
            expected_path = os.path.join(self.base_dir, info["expected_file"])
            if not os.path.exists(expected_path):
                logger.info(f"{model_key} missing. Starting download.")
                self.download_model(model_key)
            else:
                logger.info(f"{model_key} already exists at {expected_path}.")
        return True

# Example Usage
if __name__ == "__main__":
    manager = ModelManager("models")
    manager.ensure_models()

# Singleton instance
model_manager = ModelManager("models")
