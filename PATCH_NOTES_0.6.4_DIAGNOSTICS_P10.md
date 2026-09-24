# Compass 0.6.4 Diagnostics P10

- Diagnostics are now generated not only on exceptions, but also when conversion returns success with one or more materials and zero imported images.
- The bundle is written to `%LOCALAPPDATA%\ArtmachCompass\PreviewEngine\logs`.
- `Latest_Diagnostics.zip` and `Latest_Diagnostics.txt` are refreshed for this degraded-success case.
- The bundle is created before temporary conversion files are cleaned, so it includes the deployed MAXScript, numbered script, Max/Blender logs, job payload, texture manifest, FBX and generated GLB when available.
