from __future__ import annotations
import json
import struct
from pathlib import Path

class ValidationError(RuntimeError):
    pass


def validate_glb(path: Path) -> dict:
    if not path.is_file():
        raise ValidationError(f"GLB not created: {path}")
    size = path.stat().st_size
    if size < 20:
        raise ValidationError("GLB is too small")
    with path.open("rb") as f:
        magic, version, declared_length = struct.unpack("<4sII", f.read(12))
        if magic != b"glTF":
            raise ValidationError("Invalid GLB magic")
        if version != 2:
            raise ValidationError(f"Unsupported GLB version: {version}")
        if declared_length != size:
            raise ValidationError(f"GLB length mismatch: header={declared_length}, file={size}")
        chunk_length, chunk_type = struct.unpack("<II", f.read(8))
        if chunk_type != 0x4E4F534A:
            raise ValidationError("First GLB chunk is not JSON")
        json_bytes = f.read(chunk_length)
        document = json.loads(json_bytes.rstrip(b" \t\r\n\x00").decode("utf-8"))
    meshes = len(document.get("meshes", []))
    materials = len(document.get("materials", []))
    images = len(document.get("images", []))
    if meshes == 0:
        raise ValidationError("GLB has no meshes")
    return {"valid": True, "size_bytes": size, "meshes": meshes, "materials": materials, "images": images}
