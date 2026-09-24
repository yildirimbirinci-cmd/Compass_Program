# Bundled Plan3D engine

Source: yildirimbirinci-cmd/Plan3D, main tree 1283b45e5fb5c7631247a2962424f0ad8ecf950a.

Compass imports the engine through `artmach_compass.plan3d_backend` when a Plan3D operation is requested. No Plan3D buttons are added to Compass. `analyze_facade_windows` computes per-facade heights for confirmed floors; ambiguous floor assignments and missing measurement lines raise errors. `configure_exterior_door_layers` chooses a project-specific door layer; the upstream layer remains the default for older projects.

The original MaxScript transfer path is preserved as `prepare_max_transfer`. The current upstream window MaxScript exporter handles Ground Floor only; upper-floor window geometry/export, on Windows with AutoCAD and 3ds Max, still needs integration and end-to-end validation before enabling a transfer button. Keep the existing UI unchanged until panel placement is decided.
