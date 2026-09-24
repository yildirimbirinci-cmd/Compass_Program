from __future__ import annotations

import re
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".tga"}
_MODEL_FOLDER_NAMES = {"max", "model", "models", "source", "scene", "scenes", "3d"}
_PREVIEW_FOLDER_NAMES = {
    "preview", "previews", "render", "renders", "image", "images", "img",
    "thumbnail", "thumbnails", "thumb", "thumbs", "media", "gallery",
}


def _normalized_stem(path: Path | str) -> str:
    value = Path(path).stem.casefold() if isinstance(path, Path) else str(path).casefold()
    value = re.sub(r"(?:^|[\s_.-])(preview|render|thumb(?:nail)?|image|img)(?:$|[\s_.-])", " ", value)
    value = re.sub(r"(?:^|[\s_.-])0*1$", "", value)
    return re.sub(r"[\s_.-]+", "", value)


def _direct_max_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    try:
        return sorted(
            (item for item in root.iterdir() if item.is_file() and item.suffix.casefold() == ".max"),
            key=lambda item: item.name.casefold(),
        )
    except OSError:
        return []


def _max_files_in_exact_container(root: Path) -> list[Path]:
    """Return MAX files owned by exactly one asset container.

    Only the asset root itself and conventional model subfolders directly below it are
    inspected. Arbitrary descendants, ancestors and sibling asset folders are forbidden.
    """
    found = list(_direct_max_files(root))
    try:
        children = [item for item in root.iterdir() if item.is_dir() and not item.name.startswith(".")]
    except OSError:
        children = []
    for child in children:
        if child.name.casefold() in _MODEL_FOLDER_NAMES:
            found.extend(_direct_max_files(child))
    unique: dict[str, Path] = {}
    for item in found:
        try:
            key = str(item.resolve()).casefold()
        except OSError:
            key = str(item).casefold()
        unique[key] = item
    return sorted(unique.values(), key=lambda item: str(item).casefold())


def _asset_root_for_image(image: Path) -> Path:
    """Return the thumbnail's own asset root without crossing category boundaries."""
    parent = image.parent
    # Walk only through consecutive presentation-only folders. The first parent whose
    # name is not Preview/Media/Images/etc. is the asset root. This supports layouts
    # such as Asset/Media/Preview/render 01.jpg without ever climbing into the category.
    while parent.name.casefold() in _PREVIEW_FOLDER_NAMES and parent.parent != parent:
        parent = parent.parent
    return parent


def _choose_in_container(image: Path, container: Path, candidates: list[Path]) -> Path | None:
    if not candidates:
        return None
    image_key = _normalized_stem(image)
    container_key = _normalized_stem(container.name)
    keys = {key for key in (image_key, container_key) if key}
    exact = [candidate for candidate in candidates if _normalized_stem(candidate) in keys]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def resolve_max_for_thumbnail(thumbnail_path: str | Path) -> Path | None:
    """Resolve a thumbnail only inside its own asset boundary.

    The selected image's parent is the asset root, except for a single conventional
    Preview/Images/Renders-style folder where the direct parent is used as the asset
    root. The resolver never climbs farther upward. This prevents every thumbnail in a
    category from inheriting the same unrelated MAX file.
    """
    image = Path(thumbnail_path)
    if not image.is_file() or image.suffix.casefold() not in IMAGE_SUFFIXES:
        return None
    asset_root = _asset_root_for_image(image)
    candidates = _max_files_in_exact_container(asset_root)
    return _choose_in_container(image, asset_root, candidates)
