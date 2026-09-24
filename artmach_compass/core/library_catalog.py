from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LIBRARY_PATH = Path(r"C:\Users\yildi\Desktop\T2_Library\Asset Library")
DEFAULT_PROJECT_PATH = Path(r"C:\Users\yildi\Desktop\T2_Library\Project Library")
LIBRARY_PATH_ENV = "ARTMACH_COMPASS_LIBRARY_PATH"
PROJECT_PATH_ENV = "ARTMACH_COMPASS_PROJECT_PATH"

SUPPORTED_EXTENSIONS = {
    ".3ds", ".abc", ".blend", ".c4d", ".dae", ".fbx", ".glb", ".gltf",
    ".max", ".obj", ".ply", ".stl", ".usd", ".usda", ".usdc", ".vrmesh",
    ".mat", ".mtl", ".sbsar", ".vrmat",
    ".bmp", ".dds", ".exr", ".gif", ".hdr", ".heic", ".jpeg", ".jpg",
    ".png", ".psd", ".tga", ".tif", ".tiff", ".webp",
}

MODEL_EXTENSIONS = {
    ".3ds", ".abc", ".blend", ".c4d", ".dae", ".fbx", ".glb", ".gltf",
    ".max", ".obj", ".ply", ".stl", ".usd", ".usda", ".usdc", ".vrmesh",
}
MATERIAL_EXTENSIONS = {".mat", ".mtl", ".sbsar", ".vrmat"}
HDR_EXTENSIONS = {".exr", ".hdr"}


def display_folder_name(name: str) -> str:
    text = str(name or "").strip()
    text = re.sub(r"^\s*\d+\s*[_\-. ]+", "", text)
    text = re.sub(r"[_\-.]+", " ", text)
    return text.strip() or str(name)


def compact_folder_name(name: str, word_limit: int = 2) -> str:
    """Return a short tree-button label while preserving the full folder name elsewhere."""
    full_name = display_folder_name(name)
    words = full_name.split()
    if word_limit <= 0 or len(words) <= word_limit:
        return full_name
    return " ".join(words[:word_limit])


def configured_library_path() -> Path:
    override = os.environ.get(LIBRARY_PATH_ENV, "").strip()
    return Path(override) if override else DEFAULT_LIBRARY_PATH


def configured_project_path() -> Path:
    override = os.environ.get(PROJECT_PATH_ENV, "").strip()
    return Path(override) if override else DEFAULT_PROJECT_PATH


def scan_child_folders(root: Path | str) -> tuple[Path, ...]:
    """Return only direct child folders; never recurse during UI construction."""
    path = Path(root)
    if not path.is_dir():
        return ()
    try:
        return tuple(sorted(
            (item for item in path.iterdir() if item.is_dir() and not item.name.startswith(".")),
            key=lambda item: item.name.casefold(),
        ))
    except OSError:
        return ()


def classify_asset(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix in MODEL_EXTENSIONS:
        return "3D Model"
    if suffix in MATERIAL_EXTENSIONS:
        return "Material"
    if suffix in HDR_EXTENSIONS:
        return "HDRI"
    return "Texture"


@dataclass(frozen=True)
class LibraryAsset:
    name: str
    asset_type: str
    asset_format: str
    path: str


@dataclass(frozen=True)
class LibraryCategory:
    key: str
    title: str
    path: str
    assets: tuple[LibraryAsset, ...]

    @property
    def count(self) -> int:
        return len(self.assets)


def _scan_assets(folder: Path) -> tuple[LibraryAsset, ...]:
    assets: list[LibraryAsset] = []
    try:
        candidates = sorted(
            (item for item in folder.rglob("*") if item.is_file()),
            key=lambda item: str(item.relative_to(folder)).casefold(),
        )
    except OSError:
        candidates = []

    for item in candidates:
        suffix = item.suffix.casefold()
        if suffix not in SUPPORTED_EXTENSIONS:
            continue
        assets.append(
            LibraryAsset(
                name=display_folder_name(item.stem),
                asset_type=classify_asset(item),
                asset_format=suffix.lstrip(".").upper() or "FILE",
                path=str(item),
            )
        )
    return tuple(assets)


def scan_library_folders(root: Path | None = None) -> tuple[LibraryCategory, ...]:
    root = Path(root) if root is not None else configured_library_path()
    if not root.is_dir():
        return ()

    try:
        folders = sorted(
            (item for item in root.iterdir() if item.is_dir() and not item.name.startswith(".")),
            key=lambda item: item.name.casefold(),
        )
    except OSError:
        return ()

    categories: list[LibraryCategory] = []
    for folder in folders:
        categories.append(
            LibraryCategory(
                key=str(folder),
                title=display_folder_name(folder.name),
                path=str(folder),
                assets=(),
            )
        )

    return tuple(categories)


def scan_category_assets(folder: Path | str) -> tuple[LibraryAsset, ...]:
    """Scan one selected category lazily so application startup stays responsive."""
    path = Path(folder)
    if not path.is_dir():
        return ()
    return _scan_assets(path)


def scan_library(root: Path | None = None) -> tuple[LibraryCategory, ...]:
    """Compatibility helper that performs a complete scan when explicitly requested."""
    categories = []
    for category in scan_library_folders(root):
        categories.append(
            LibraryCategory(
                key=category.key,
                title=category.title,
                path=category.path,
                assets=scan_category_assets(category.path),
            )
        )
    return tuple(categories)

