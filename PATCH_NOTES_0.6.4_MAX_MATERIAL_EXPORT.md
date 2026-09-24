# Compass GLB Engine v0.6.4 - MAX Material Export Patch

- Converts renderer-specific Corona/V-Ray materials on temporary export meshes to FBX-safe Standard materials.
- Preserves Multi/Sub material structure and material IDs.
- Recursively resolves valid diffuse/albedo/base bitmap files while ignoring empty procedural map references.
- Preserves base color and opacity as fallback values.
- Embeds valid textures in the intermediate FBX so Blender can package them into GLB.
- Does not modify or save the source MAX file.
