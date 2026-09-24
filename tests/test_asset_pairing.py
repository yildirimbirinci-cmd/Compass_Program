from pathlib import Path

from artmach_compass.core.asset_pairing import resolve_max_for_thumbnail


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'x')
    return path


def test_does_not_cross_into_sibling_asset(tmp_path: Path):
    category = tmp_path / 'Cars'
    a3 = category / 'Audi_A3'
    a6 = category / 'Audi_A6'
    image = touch(a3 / 'Audi A3 01.jpg')
    touch(a6 / 'Audi_A6.max')
    assert resolve_max_for_thumbnail(image) is None


def test_matches_same_asset_container(tmp_path: Path):
    asset = tmp_path / 'Audi_A3'
    image = touch(asset / 'Audi A3 01.jpg')
    model = touch(asset / 'Audi_A3.max')
    assert resolve_max_for_thumbnail(image) == model


def test_matches_parent_of_preview_folder(tmp_path: Path):
    asset = tmp_path / 'Audi_A3'
    image = touch(asset / 'Preview' / 'Audi A3 01.jpg')
    model = touch(asset / 'Audi_A3.max')
    assert resolve_max_for_thumbnail(image) == model


def test_supports_model_subfolder_without_scanning_siblings(tmp_path: Path):
    asset = tmp_path / 'Audi_A3'
    image = touch(asset / 'Audi A3 01.jpg')
    model = touch(asset / 'Max' / 'Audi_A3.max')
    touch(tmp_path / 'Audi_A6' / 'Max' / 'Audi_A6.max')
    assert resolve_max_for_thumbnail(image) == model


def test_nearest_ancestor_owns_thumbnail_and_never_uses_sibling(tmp_path):
    first = tmp_path / "Audi_A3"
    second = tmp_path / "Audi_A6"
    image = first / "Media" / "Preview" / "render 01.jpg"
    correct = first / "Audi_A3.max"
    wrong = second / "Audi_A6.max"
    image.parent.mkdir(parents=True)
    second.mkdir(parents=True)
    image.write_bytes(b"jpg")
    correct.write_bytes(b"max")
    wrong.write_bytes(b"max")
    assert resolve_max_for_thumbnail(image) == correct


def test_duplicate_thumbnail_names_resolve_to_different_asset_max_files(tmp_path):
    resolved = []
    for asset_name in ("Audi_A3", "Audi_A6"):
        root = tmp_path / asset_name
        image = root / "renders" / "render 01.jpg"
        model = root / f"{asset_name}.max"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"jpg")
        model.write_bytes(b"max")
        resolved.append(resolve_max_for_thumbnail(image))
    assert resolved[0] != resolved[1]


def test_does_not_climb_to_category_level_max(tmp_path):
    category = tmp_path / "04_MATERIALS"
    asset_a = category / "Asset_A"
    asset_b = category / "Asset_B"
    asset_a.mkdir(parents=True)
    asset_b.mkdir(parents=True)
    unrelated = category / "Sofa_set.max"
    unrelated.write_bytes(b"max")
    image_a = asset_a / "render 01.jpg"
    image_b = asset_b / "render 01.jpg"
    image_a.write_bytes(b"jpg")
    image_b.write_bytes(b"jpg")
    assert resolve_max_for_thumbnail(image_a) is None
    assert resolve_max_for_thumbnail(image_b) is None


def test_preview_folder_uses_only_direct_asset_parent(tmp_path):
    category = tmp_path / "Vehicles"
    asset = category / "Audi A3 01"
    preview = asset / "Preview"
    preview.mkdir(parents=True)
    model = asset / "Audi A3 01.max"
    model.write_bytes(b"max")
    image = preview / "render 01.jpg"
    image.write_bytes(b"jpg")
    assert resolve_max_for_thumbnail(image) == model
