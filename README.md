# 0.6.4 widened scrollbar interaction area

- Expanded the transparent scrollbar hit strip from 5 px to 12 px while preserving the 2 px orange visual thumb.
- Removed the conflicting 4 px theme override so source and packaged builds use the same interaction geometry.
- Increased the Library-content-to-left-rail clearance by 4 px.
- Moved the visible gray rail and orange scroll thumb out of the rotating face.
- The rail now remains fixed while Library / Project / AI card transitions run.
- The hidden face-owned scrollbar remains only as the scroll-state model.

- Hover outline core reduced to 0.2 px; hovered button label and marker turn orange.
- Fixed-length scroll thumbs now drag proportionally with the pointer instead of jumping.
- Wheel movement uses pixel deltas when available and a page-relative step for standard wheels.
- Library/Project vertical scrollbar now matches the thumbnail panel: idle-hidden thumb and full-height grayscale faded rail.

# 0.3.60 changes

- Horizontal and vertical orange scrollbar interaction strips are now exactly 5 px while retaining their existing painted appearance and behavior.

- Moves the Library panel 5 px closer to the left application edge at desktop and medium breakpoints.
- Adds 10 px more clearance between Library navigation buttons and the Library scrollbar.
- Uses content-aware Library button widths so short and long category labels no longer produce identical button lengths.

- Library and Asset Inspector use one shared responsive width.
- Workspace outer left/right margins remain identical.
- Library trailing content margin is derived from the active workspace gap, the 20 px Inspector inner margin, and the 5 px scrollbar width, so both separator-to-content distances mirror each other.


- All orange scrollbar thumbs now use a fixed 64 px length independent of list size.
- Active Library/Project buttons keep a 1 px blue outline with a breathing blue glow.
- Hovered navigation buttons show a 1 px orange outline with a soft orange glow.

- Added a direction-aware orange comet trail behind every vertical and horizontal scrollbar thumb.
- Changed all scrollbar rails to a balanced grayscale tone.
- Thumbnail rail keeps its full-height top/bottom opacity fade and the thumb still hides while idle.

- Folder navigation now uses single-open-branch accordion behavior at every level.
- Horizontal and vertical scrollbars stay dark while idle and become active on hover, drag, or scrolling.

# Artmach Compass — Windows UI Prototype 0.6.4

Artmach Compass 0.6.4 is a Windows-only, local desktop interface prototype. It contains
no T2 paths, credentials, assets, server settings, NAS/FTP connection, login or
account setup.

## Verified panel map

The workspace mapping is intentionally explicit:

| Position | Panel | Behavior |
| --- | --- | --- |
| Left | Library / Project / AI | Only the three tab headings switch faces; category rows activate their own content. |
| Middle | Smart Workspace / Thumbnails | Keeps the active page beneath a dedicated startup/idle cover; it never flips. |
| Right | Asset Inspector | Updates when an asset thumbnail is selected. |

The complete window shares one continuous vertical graphite gradient. It opens
into lighter gray toward the top, stays dark through the middle and falls into
black toward the bottom. Panel surfaces are transparent, so their resting
boundaries cannot be seen. The workspace palette remains graphite. Blue is
reserved for active navigation text and markers.

There are no permanent divider or contour lines. The left panel shows a soft
neutral-gray moving contour trace only while hovered or during its flip.

## Startup and idle cover

- The middle panel opens on the Compass standby view.
- After activation, 5 seconds without mouse, wheel, keyboard, touch or tablet
  input returns the application to the same standby view.
- The open middle-panel state is preserved but disabled behind the cover.
- All panels and controls are disabled while standby is active.
- Standby dims the live, correctly positioned interface with one full-window
  compositor. It does not create panel copies or cache transparent panel pixels.
- Standby uses a single uniform dimming compositor; no full-window light beam is rendered.
- Background animation timers, including the moving panel contour, are paused.
- Only a left click inside the outer orbit starts the centered logo glow. After that glow completes
  does a fast opacity transition reveal the preserved active panel.
- The official `ArtmachCompass.png` mark is rendered from its high-resolution source.
- Its dark icon plate is keyed out so the shared window gradient remains visible.
- Standby and active Preview share the exact same canvas rectangle and four-ring
  geometry. Standby adds the orange comet and trail, partial arc and center glow
  and logo; active mode keeps only the static rings behind its content.

The logo is not rendered on the normal active workspace face. On standby it is
rendered in grayscale at 50% opacity. The Library, Project and AI tabs are
equally distributed across the left panel, with the orange indicator centered
directly beneath the active label. The redundant Compass/section eyebrow has
been removed. Button colors are unchanged in this build.

## Responsive behavior

- The application opens maximized.
- The workspace fills all available width and height.
- Default restored window: `1440 × 900 px`
- Minimum supported viewport: `320 × 480 px`

The panels form three columns on desktop widths. Compact widths use narrower
side panels. Below `820 px`, the same left/middle/right semantic order becomes
a vertical stack so content does not overflow the window.

## Requirements for building on Windows

- Windows 10/11 x64
- Python 3.11 x64
- Inno Setup 6, only when creating the Setup EXE

## Direct installation

Double-click `Install_Prototype.cmd` and approve the Windows administrator
request. The script builds the application, installs it under
`C:\Program Files\Artmach Compass`, creates the Artmach Compass desktop
shortcut and launches the application.

## Build the installer

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

Output:

```text
dist_installer\Artmach_Compass_Setup_0.6.4.exe
```

## Source test

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_source.ps1
```

The application keeps the native Windows title bar, native edge/corner resizing,
Snap Layouts, Win+Arrow and Print Screen behavior.


## 0.3.60 background quality
The shared background is now rendered as a full-resolution, one-LSB spatially dithered image instead of an 8-bit Qt gradient. This removes visible contour bands on large dark displays.

## Local library integration (0.3.60)
Compass scans `C:\Users\yildi\Desktop\T2_Library` at startup. Each first-level folder becomes a Library panel button, the number at the right is the recursive count of supported asset files, and clicking a button fills the center grid from that folder. Set `ARTMACH_COMPASS_LIBRARY_PATH` to override the path without changing source code.


## Local folder integration (0.3.60)
- Library panel root: `C:\Users\yildi\Desktop\T2_Library\Asset Library`
- Project panel root: `C:\Users\yildi\Desktop\T2_Library\Project Library`
- Folder buttons expand lazily into nested child buttons; no recursive startup scan is performed.

## 0.3.60 library tree layout
- Folder-row gaps are uniform at every nesting level.
- Nested folder buttons use a lower 30 px height while preserving the existing width.
- Chevron/arrow indicators were removed; clicking a folder row still expands or collapses its children.
- The folder panel now provides an as-needed horizontal scrollbar at the bottom when a full folder name exceeds the visible panel width.

## 0.3.60 scrollbar system
- Every scroll area uses the same custom reactive scrollbar renderer.
- Scroll thumbs are 2 px and orange; the underlying rail is 1.5 px.
- Mouse-wheel scrolling reveals scroll thumbs in a subdued orange; hovering or dragging promotes them to the fully saturated active orange.
- The thumbnail panel hides its thumb while idle and keeps a full-height orange rail whose opacity fades at the top and bottom.
## 0.6.4 dashboard first pass
- Added a production-style top command bar with T2 branding, module buttons, global search and quick commands.
- Reframed Library, Workspace and Asset Inspector as bordered dashboard panels.
- Added a persistent bottom connection/status strip.
- Updated active navigation and asset cards to the orange-accent visual language.
- Preserved the existing Library/Project/AI navigation, thumbnail browser, preview, inspector and standby controller.


## 0.6.4 thumbnail acceleration
Uses the T2 Manager thumbnail strategy: per-folder discovery cache, asset-to-preview memory cache, persistent pre-scaled JPG cache under LocalAppData, and QPixmap reuse. The top bar now displays only the Compass logo.

## 0.6.4 center workspace layout

The center workspace now contains only the requested panels: panel 7 and panel 9 share the top row at equal width, while panel 8 spans horizontally beneath them. The former panel 11 activity/message region is not part of the center workspace. Selecting a 01 thumbnail updates both the viewer and the lower preview/detail strip.


## 0.6.4 integrated GLB preview engine

- Selecting a valid `.max` asset enables **Generate Preview** in Panel 9.
- Conversion runs asynchronously through `3dsmaxbatch.exe` and Blender background mode; the Compass interface remains responsive.
- The generated `<asset>_preview.glb` is saved next to the selected MAX file.
- Conversion logs and temporary files are kept under `%LOCALAPPDATA%\ArtmachCompass\PreviewEngine`, never under Program Files.
- Normal visible 3ds Max fallback was removed; conversion is background-only.
- Corona and V-Ray reference assets were successfully validated by the standalone engine before integration.
