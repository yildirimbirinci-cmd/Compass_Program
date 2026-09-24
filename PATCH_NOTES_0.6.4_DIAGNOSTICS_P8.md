# Compass GLB Engine v0.6.4 - Guaranteed Diagnostics p8

- Diagnostics now cover preflight failures too: invalid MAX source, missing 3ds Max, missing Blender, missing 3dsmaxbatch, and missing MAXScript.
- Added an emergency diagnostics fallback if the normal support bundle itself fails.
- `Latest_Diagnostics.zip` and `Latest_Diagnostics.txt` are always refreshed after any conversion failure.
- Diagnostics remain under `%LOCALAPPDATA%\ArtmachCompass\Diagnostics`.
- Verified with an actual forced preflight failure; the ZIP and aliases were created successfully.
