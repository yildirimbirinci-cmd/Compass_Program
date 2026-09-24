# Compass GLB Engine 0.6.4 - Diagnostics p6

- Removed the ambiguous MAXScript `) else (` boundary from the diffuse texture branch.
- Failed conversions now automatically create one `*_diagnostics.zip` file in `%LOCALAPPDATA%\ArtmachCompass\PreviewEngine\logs`.
- The bundle contains the exact deployed `run_job.ms`, a numbered source copy, Max batch/listener/system logs, Blender log when available, job JSON, engine configuration snapshot, texture manifest, Max report, and intermediate files created before failure.
- The conversion error shown by Compass includes the full path of the diagnostics ZIP.
- For the next failure, send only the generated `*_diagnostics.zip` file.
