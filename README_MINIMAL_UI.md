# Artmach Compass 0.6.4 — Clean standby compositor

This build keeps the verified panel assignment and the viewport-filling,
graphite surface while turning the center logo view into a dedicated standby
cover:

- Left: working Library, Project and AI tabs plus their category faces.
- Middle: animated Preview and an activated thumbnail browser beneath the startup/5-second idle cover.
- Right: Asset Inspector updated by thumbnail selection.

The search bar is temporarily removed while its new location is being
designed. The workspace fills the complete window. On desktop widths, the
Library browser displays 50 equal square thumbnail cards in four columns with vertical scrolling.

The existing button palette has not been changed.

The idle cover and Windows application icon use the supplied Artmach Compass
artwork. On standby, the center logo is grayscale at 50% opacity. The left
panel's Library, Project and AI tabs are evenly distributed across the panel;
the 30 × 2 px orange indicator remains centered directly beneath the active
label. The redundant Compass/section eyebrow has been removed.

Standby shows four rings, the moving orange comet and trail, the partial arc,
center glow and grayscale logo. Active mode keeps only the same four rings as a
static background layer; the logo, comet, trail and arc disappear.
Only a click inside the outer ring starts the logo glow and reveals the
preserved active panel with a fast opacity transition.

The standby view uses the real interface under one dimming layer. It does not
capture, hide, duplicate or replay the side panels. The standby layer only dims
the live interface and does not render an ambient beam.

This package contains Windows launch, build and installer files only.


## Local folder integration (0.6.4)
- Library panel root: `C:\Users\yildi\Desktop\T2_Library\Asset Library`
- Project panel root: `C:\Users\yildi\Desktop\T2_Library\Project Library`
- Folder buttons expand lazily into nested child buttons; no recursive startup scan is performed.
