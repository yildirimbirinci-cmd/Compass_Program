# Compass GLB Engine v0.6.4 - Texture Image Fix p2

- CoronaBitmap, VRayBitmap and other bitmap-like maps are detected by their file path instead of exact class name.
- Renderer-specific maps are always normalized to native 3ds Max `BitmapTexture` before FBX export.
- Relative texture paths are resolved through 3ds Max path configuration.
- Additional Corona/V-Ray base-color and albedo property names are searched.
- Nested map arrays are traversed, allowing textures inside composite/mix style maps to be found.
- UV tiling, offset and rotation are copied when available.
- This specifically fixes successful GLB files reporting `materials > 0` but `images = 0`.
