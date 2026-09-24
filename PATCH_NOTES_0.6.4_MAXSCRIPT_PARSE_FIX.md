# Compass GLB Engine v0.6.4 - MAXScript Parse Fix p3

- Fixed invalid MAXScript `if ... do (...) else ...` syntax in `findBitmapInMap`.
- Replaced the conditional with the valid `if ... then (...) else if ... then (...)` form.
- Added a regression test to prevent the invalid `do/else` form from returning.
- This fix allows `run_job.ms` to parse in 3ds Max 2020 and lets the FBX/GLB conversion pipeline start.
