from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

import bpy

PREFIX = "COMPASS_BLENDER"


def log(message: str) -> None:
    print(f"{PREFIX}: {message}", flush=True)


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--texture-manifest", default="")
    return parser.parse_args(argv)


def operator_properties(operator) -> set[str]:
    """Return the keyword properties supported by a Blender operator."""
    try:
        return {prop.identifier for prop in operator.get_rna_type().properties}
    except Exception:
        return set()


def call_compatible(operator, requested: dict, label: str):
    supported = operator_properties(operator)
    if supported:
        kwargs = {key: value for key, value in requested.items() if key in supported}
        skipped = sorted(set(requested) - set(kwargs))
        if skipped:
            log(f"{label}: ignored unsupported options: {', '.join(skipped)}")
    else:
        kwargs = requested

    log(f"{label}: calling with {len(kwargs)} options")
    result = operator(**kwargs)
    log(f"{label}: result={sorted(result)}")
    if "CANCELLED" in result:
        raise RuntimeError(f"{label} was cancelled by Blender")
    if "FINISHED" not in result:
        raise RuntimeError(f"{label} returned an unexpected result: {result}")
    return result



def _ensure_principled(material):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    output = next((node for node in nodes if node.type == "OUTPUT_MATERIAL"), None)
    if output is None:
        output = nodes.new("ShaderNodeOutputMaterial")
    if not bsdf.outputs["BSDF"].is_linked:
        material.node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return bsdf


def apply_texture_manifest(path: Path) -> int:
    if not path.is_file():
        log(f"Texture manifest not found: {path}")
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"Texture manifest read failed: {exc}")
        return 0
    records = payload.get("materials", []) if isinstance(payload, dict) else []
    by_name = {str(item.get("material", "")).casefold(): item for item in records if isinstance(item, dict)}
    assigned = 0
    for material in bpy.data.materials:
        item = by_name.get(material.name.casefold())
        if item is None:
            # FBX may add numeric suffixes when material names collide.
            base = material.name.rsplit(".", 1)[0].casefold()
            item = by_name.get(base)
        if item is None:
            continue
        texture_path = Path(str(item.get("texture", "")))
        if not texture_path.is_file():
            log(f"Texture missing for material {material.name}: {texture_path}")
            continue
        try:
            image = bpy.data.images.load(str(texture_path), check_existing=True)
            bsdf = _ensure_principled(material)
            node = material.node_tree.nodes.new("ShaderNodeTexImage")
            node.image = image
            node.label = "Compass recovered base color"
            material.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
            if "Alpha" in node.outputs and "Alpha" in bsdf.inputs:
                material.node_tree.links.new(node.outputs["Alpha"], bsdf.inputs["Alpha"])
            assigned += 1
            log(f"Recovered texture for {material.name}: {texture_path}")
        except Exception as exc:
            log(f"Texture recovery failed for {material.name}: {exc}")
    log(f"Texture manifest recovery assigned={assigned}, records={len(records)}")
    return assigned

def main() -> None:
    args = parse_args()
    src = Path(args.input).resolve()
    dst = Path(args.output).resolve()
    texture_manifest = Path(args.texture_manifest).resolve() if args.texture_manifest else None

    log(f"Blender version={bpy.app.version_string}")
    log(f"Input={src}")
    log(f"Output={dst}")

    if not src.is_file():
        raise FileNotFoundError(f"FBX input does not exist: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()

    factory_result = bpy.ops.wm.read_factory_settings(use_empty=True)
    log(f"Factory reset result={sorted(factory_result)}")

    call_compatible(
        bpy.ops.import_scene.fbx,
        {
            "filepath": str(src),
            "use_image_search": True,
            "automatic_bone_orientation": False,
        },
        "FBX import",
    )

    scene_objects = list(bpy.context.scene.objects)
    mesh_objects = [obj for obj in scene_objects if obj.type == "MESH"]
    material_count = len(bpy.data.materials)
    image_count = len(bpy.data.images)
    log(
        "Imported scene: "
        f"objects={len(scene_objects)}, meshes={len(mesh_objects)}, "
        f"materials={material_count}, images={image_count}"
    )

    if not mesh_objects:
        raise RuntimeError("No mesh objects imported from FBX")

    if image_count == 0 and texture_manifest is not None:
        recovered = apply_texture_manifest(texture_manifest)
        if recovered:
            image_count = len(bpy.data.images)
            log(f"Post-recovery images={image_count}")

    valid_meshes = 0
    for obj in mesh_objects:
        if obj.data is None:
            continue
        obj.data.validate(clean_customdata=False)
        obj.data.update()
        valid_meshes += 1
    log(f"Validated mesh datablocks={valid_meshes}")

    export_options = {
        "filepath": str(dst),
        "export_format": "GLB",
        "export_yup": True,
        "export_apply": True,
        "export_texcoords": True,
        "export_normals": True,
        "export_tangents": True,
        "export_materials": "EXPORT",
        # Blender 5.x removed export_images. It is intentionally requested
        # here and filtered dynamically so the same script also works with
        # older Blender releases that still support it.
        "export_images": "AUTO",
        "export_cameras": False,
        "export_lights": False,
        "export_animations": False,
    }
    call_compatible(bpy.ops.export_scene.gltf, export_options, "GLB export")

    if not dst.is_file():
        raise RuntimeError(f"GLB export reported success but no file was created: {dst}")
    if dst.stat().st_size <= 20:
        raise RuntimeError(f"GLB file is unexpectedly small: {dst.stat().st_size} bytes")

    log(f"GLB created successfully: {dst} ({dst.stat().st_size} bytes)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"FATAL: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        # Blender may otherwise quit with code 0 even after a Python traceback.
        os._exit(1)
