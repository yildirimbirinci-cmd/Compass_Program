# Compass GLB Engine v0.6.4 - T2 Texture Recovery p4

- Added a MAXScript-generated material/texture manifest beside each temporary FBX.
- Added CoronaBitmap, VRayBitmap, VRayHDRI and generic renderer path-property discovery.
- Added relative path recovery against the loaded MAX file folder and 3ds Max path configuration.
- Added a full texture-map fallback scan for legacy renderer materials.
- Added Blender-side material texture recovery when FBX imports with zero images.
- Preserved the existing FBX embedded-texture path; the manifest is a fallback, not a replacement.
- Added detailed Max and Blender log lines for mapped, missing and recovered textures.
- Integrated the T2 Manager path-handling rule that BitmapTexture.filename is the writable source path.
