# Bundled Plan3D engine

Source: yildirimbirinci-cmd/Plan3D, main tree 1283b45e5fb5c7631247a2962424f0ad8ecf950a.

`artmach_compass.plan3d_backend` imports the engine lazily; no Plan3D buttons are placed into Compass. `analyze_facade_windows` measures all confirmed floors from the lowest `C Ölçü` line inside each selected facade. `prepare_max_transfer` prepares a MaxScript using per-floor physical windows, facade measurements and existing wall/floor/door exports. It never executes 3ds Max itself.

A missing datum, unmatched floor/window, or incomplete assignment raises an error instead of producing a partial transfer. Existing exterior-door layer remains the default; `configure_exterior_door_layers` accepts a different project-specific source. The source engine's standalone UI modules are bundled to preserve internal dependencies but are not instantiated or displayed by the Compass adapter.

A live end-to-end Windows/AutoCAD/3ds Max check against Ground/First/Second Floor drawings is still required before adding a transfer button. The Compass interface remains untouched while panel placement is undecided.
