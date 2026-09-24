# Compass GLB Engine v0.6.4 - Diagnostics Discoverability p7

- Failed conversions now write support bundles to `%LOCALAPPDATA%\ArtmachCompass\Diagnostics`.
- `Latest_Diagnostics.zip` always points to the most recently created support bundle.
- `Latest_Diagnostics.txt` records the full timestamped ZIP path.
- On conversion failure, Compass opens the Diagnostics folder automatically.
- The UI displays the generated diagnostic ZIP filename instead of hiding it inside a long error message.
- The worker now transports the diagnostics path separately from the error text.
