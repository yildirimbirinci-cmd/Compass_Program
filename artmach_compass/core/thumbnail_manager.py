from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from threading import RLock

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage


class ThumbnailManager:
    """Fast 01-preview resolver with memory and persistent disk caches."""

    IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".tga"}
    _lock = RLock()
    _folder_cache: dict[str, tuple[Path, ...]] = {}
    _source_cache: dict[str, str] = {}
    _thumb_cache: dict[str, str] = {}

    def __init__(self) -> None:
        local_appdata = os.getenv("LOCALAPPDATA")
        base = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        self.cache_root = base / "ArtmachCompass" / "ThumbnailCache"
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self._number_re = re.compile(r"(^|[^0-9])01([^0-9]|$)")

    @staticmethod
    def _resolved(path: Path) -> str:
        try:
            return str(path.resolve()).casefold()
        except OSError:
            return str(path).casefold()

    def _folder_key(self, folder: Path) -> str:
        try:
            return f"{self._resolved(folder)}|{folder.stat().st_mtime_ns}"
        except OSError:
            return self._resolved(folder)

    def _collect_01_images(self, folder: Path) -> tuple[Path, ...]:
        if not folder.is_dir():
            return ()
        key = self._folder_key(folder)
        with self._lock:
            cached = self._folder_cache.get(key)
            if cached is not None:
                return cached
        images: list[Path] = []
        try:
            for item in folder.iterdir():
                if not item.is_file() or item.suffix.casefold() not in self.IMAGE_SUFFIXES:
                    continue
                stem = item.stem.casefold()
                if stem.endswith("01") or self._number_re.search(stem):
                    images.append(item)
        except OSError:
            images = []
        images.sort(key=lambda item: item.name.casefold())
        result = tuple(images)
        with self._lock:
            self._folder_cache[key] = result
        return result

    def is_image(self, asset_path: str | Path) -> bool:
        """Return True only for existing files with a supported image suffix."""
        if not asset_path:
            return False
        path = Path(asset_path)
        return path.is_file() and path.suffix.casefold() in self.IMAGE_SUFFIXES

    def is_01_image(self, asset_path: str | Path) -> bool:
        """Return True only for image files whose filename identifies preview 01."""
        if not asset_path:
            return False
        path = Path(asset_path)
        if not path.is_file() or path.suffix.casefold() not in self.IMAGE_SUFFIXES:
            return False
        stem = path.stem.casefold()
        return stem.endswith("01") or bool(self._number_re.search(stem))

    def find_source(self, asset_path: str | Path) -> Path | None:
        if not asset_path:
            return None
        source = Path(asset_path)
        try:
            stat = source.stat()
            source_key = f"{self._resolved(source)}|{stat.st_mtime_ns}|{stat.st_size}"
        except OSError:
            source_key = self._resolved(source)
        with self._lock:
            if source_key in self._source_cache:
                value = self._source_cache[source_key]
                return Path(value) if value else None
        if source.is_file() and source.suffix.casefold() in self.IMAGE_SUFFIXES:
            # Direct image selections (including Texture mode) preview themselves.
            result = source
        else:
            folder = source if source.is_dir() else source.parent
            candidates = self._collect_01_images(folder)
            result = None
            if candidates:
                asset_stem = source.stem.casefold()
                normalized = re.sub(r"[\s_.-]+", "", asset_stem)
                ranked = sorted(candidates, key=lambda item: (
                    0 if re.sub(r"[\s_.-]+", "", item.stem.casefold()).startswith(normalized) else 1,
                    item.name.casefold(),
                ))
                result = ranked[0]
        with self._lock:
            self._source_cache[source_key] = str(result) if result else ""
        return result

    def _cache_key(self, source: Path, width: int, height: int) -> str:
        try:
            stat = source.stat()
            value = f"{source.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{width}x{height}"
        except OSError:
            value = f"{source}|{width}x{height}"
        return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()

    def find_thumbnail(self, asset_path: str | Path, width: int = 320, height: int = 184) -> Path | None:
        source = self.find_source(asset_path)
        if source is None:
            return None
        key = self._cache_key(source, width, height)
        with self._lock:
            known = self._thumb_cache.get(key)
            if known and Path(known).exists():
                return Path(known)
        cached = self.cache_root / f"{key}.jpg"
        if cached.exists():
            with self._lock:
                self._thumb_cache[key] = str(cached)
            return cached
        try:
            image = QImage(str(source))
            if image.isNull():
                return source
            image = image.scaled(QSize(width, height), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if not image.isNull() and image.save(str(cached), "JPG", 84):
                with self._lock:
                    self._thumb_cache[key] = str(cached)
                return cached
        except Exception:
            return source
        return source

    @classmethod
    def clear_memory_cache(cls) -> None:
        with cls._lock:
            cls._folder_cache.clear()
            cls._source_cache.clear()
            cls._thumb_cache.clear()
