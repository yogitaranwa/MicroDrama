"""Asset management and reference image preparation for Magic Hour."""

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, Union
from PIL import Image
from ..config import UPLOADS_CACHE_FILE, OUTPUT_DIR
from ..models import Character


class AssetManager:
    """Handles character reference images and uploads to Magic Hour."""

    def __init__(self, magic_hour_client=None, cache_file: Optional[Path] = None):
        self.client = magic_hour_client
        self.cache_file = cache_file or UPLOADS_CACHE_FILE
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.vertical_dir = OUTPUT_DIR / "vertical_references"
        self.vertical_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> Dict[str, str]:
        if not self.cache_file.exists():
            return {}
        try:
            return json.loads(self.cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_cache(self, cache: Dict[str, str]) -> None:
        self.cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    def ensure_vertical_aspect(self, image_path: Union[str, Path]) -> Path:
        """Verify 9:16 aspect ratio or center-crop image to vertical portrait."""
        p = Path(image_path)
        if not p.is_file():
            raise FileNotFoundError(f"Reference image not found: {p}")

        with Image.open(p) as im:
            im = im.convert("RGB")
            w, h = im.size
            current_ratio = w / h
            target_ratio = 9 / 16

            if abs(current_ratio - target_ratio) < 0.03:
                return p  # Already vertical 9:16

            # Center crop to 9:16
            if current_ratio > target_ratio:
                new_w, new_h = round(h * target_ratio), h
            else:
                new_w, new_h = w, round(w / target_ratio)

            left = (w - new_w) // 2
            top = (h - new_h) // 2
            cropped = im.crop((left, top, left + new_w, top + new_h))

            digest = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
            out_path = self.vertical_dir / f"{p.stem}_{digest}_9x16.png"
            cropped.save(out_path, format="PNG")
            return out_path

    def upload_reference(self, image_path: Union[str, Path]) -> str:
        """Ensure vertical crop and upload reference image to Magic Hour files API."""
        vertical_path = self.ensure_vertical_aspect(image_path)
        digest = hashlib.sha256(vertical_path.read_bytes()).hexdigest()

        cache = self._load_cache()
        if digest in cache:
            return cache[digest]

        if not self.client:
            # Mock / offline mode fallback
            fake_asset_path = f"api-assets/mock_{digest[:10]}.png"
            cache[digest] = fake_asset_path
            self._save_cache(cache)
            return fake_asset_path

        # Real upload to Magic Hour
        try:
            asset_path = self.client.v1.files.upload_file(file=vertical_path)
            cache[digest] = asset_path
            self._save_cache(cache)
            return asset_path
        except Exception as e:
            raise RuntimeError(f"Failed to upload reference image '{vertical_path.name}' to Magic Hour: {e}") from e

    def prepare_cast_references(self, cast: list[Character]) -> list[Character]:
        """Upload all character reference images and attach api_asset_path."""
        for character in cast:
            if character.reference_image_path and not character.api_asset_path:
                ref_path = Path(character.reference_image_path)
                if ref_path.is_file():
                    character.api_asset_path = self.upload_reference(ref_path)
        return cast
