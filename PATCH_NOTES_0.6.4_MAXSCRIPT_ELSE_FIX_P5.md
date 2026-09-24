# Compass GLB Engine v0.6.4 - MAXScript else parse fix p5

- Fixed the invalid MAXScript form `if ... do (...) else (...)` in `run_job.ms`.
- The diffuse texture export branch now uses the valid `if ... then (...) else (...)` form.
- Added a regression test that rejects any parenthesized `do` branch followed by `else`.
- No source `.max` asset is modified by this change.
