# Compass 0.6.4 - Integrated Preview Generator

This build integrates the validated Compass GLB Conversion Engine 0.1.9 into the Compass interface.

## User flow

1. Select a `.max` asset in Library.
2. Click **GENERATE PREVIEW** in Panel 9.
3. Compass runs 3ds Max Batch and Blender in the background.
4. `<asset-name>_preview.glb` is written beside the MAX file.
5. Progress and validation counts are shown inside Compass.

## Runtime data

Logs and temporary conversion files are written to:

`%LOCALAPPDATA%\ArtmachCompass\PreviewEngine`

The application installation directory remains read-only.

## Important

Chaos Scatter must remain disabled or correctly installed when it causes 3ds Max startup errors. The integrated pipeline intentionally does not launch visible desktop 3ds Max as a fallback.

## 0.6.4 thumbnail-to-MAX safety rule

Preview generation is now anchored to the image currently selected in the thumbnail panel. Compass resolves a matching `.max` file only inside the selected image's asset folder (or a conventional parent preview folder), rejects ambiguous matches, and never generates a preview from an unrelated MAX selection.

## 0.6.4 corrections
- Thumbnail/MAX pairing is now restricted to the selected thumbnail's own asset container.
- Category sibling folders are never searched, preventing unrelated thumbnails from sharing one MAX file.
- Conventional `Max`, `Model`, `Source`, `Scene`, and `3D` subfolders remain supported.
- 3ds Max exports evaluated mesh snapshots so wrapper/proxy/group nodes do not arrive in Blender as EMPTY objects.

## 0.6.4 strict asset-boundary pairing

Thumbnail-to-MAX resolution no longer climbs through up to six ancestors. A thumbnail
may resolve a MAX only in its own folder, or in the direct parent when the image lives
inside a conventional Preview/Images/Renders folder. Category roots and sibling asset
folders are never considered. This removes the defect where unrelated thumbnails could
all inherit the same MAX file higher in the library tree.
