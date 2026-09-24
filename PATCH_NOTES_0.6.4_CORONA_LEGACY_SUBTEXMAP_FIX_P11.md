# Compass GLB Engine v0.6.4 - Corona Legacy SubTexmap Fix p11

## Problem
Diagnostics showed that 3ds Max completed FBX and GLB conversion but exported 2-3 materials with 0 images. The deployed MAXScript reported `No diffuse texture found` for `CoronaLegacyMtl` materials and generated an empty texture manifest.

## Root cause
Corona Legacy materials in 3ds Max 2020 can expose texture inputs through the native sub-texmap API (`getNumSubTexmaps`, `getSubTexmap`, `getSubTexmapSlotName`) without exposing a stable renderer-version-specific property name through `getPropNames`.

## Fix
- Added recursive native sub-texmap traversal for materials and texture maps.
- Prioritizes sub-texmap slots named diffuse, albedo, base, or color.
- Falls back to the first valid file-backed texture when a slot name is unavailable.
- Preserves existing property-based lookup for Standard, Corona, and V-Ray materials.
- Increased recursive map depth to support nested color-correction/composite chains.
- Added listener logging for the exact matched slot and index.
- Procedural maps without a real file path remain excluded from FBX/GLB export.

## Expected result
`CoronaLegacyMtl` diffuse/albedo bitmaps are converted to native `BitmapTexture`, embedded through FBX, and visible as GLB images. The texture manifest should no longer be empty for file-textured materials.
