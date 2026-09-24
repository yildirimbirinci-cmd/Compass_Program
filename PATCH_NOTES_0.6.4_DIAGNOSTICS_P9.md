# Compass 0.6.4 Diagnostics p9

- Diagnostics now write to `%LOCALAPPDATA%\ArtmachCompass\PreviewEngine\logs`, the folder already visible in the runtime tree.
- `Latest_Diagnostics.zip` and `Latest_Diagnostics.txt` are always updated there.
- Preview initialization, 3ds Max detection, Blender detection, configuration loading, and other failures that happen before `ConversionPipeline.convert()` now create an emergency diagnostic ZIP.
- Pipeline failures and pre-pipeline failures use the same log location.
