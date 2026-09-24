# Approved interface rules — 0.3.21 clean standby compositing baseline

- The logo view appears only at startup and after 5 seconds without user input.
- The open middle-panel state remains preserved and disabled beneath the cover.
- Only a click inside the outer orbit runs the logo glow before a fast opacity reveal.
- The official Artmach Compass logo asset is used; no replacement mark is redrawn.
- The icon plate is transparent so the shared background continues behind it.
- The logo is reduced and centered within the orbit system.
- Standby and Preview use one shared four-ring renderer and identical geometry.
- Standby adds the grayscale logo, orange comet/trail, partial arc and center glow.
- Active mode keeps only the static rings behind the workspace content.
- Standby uses one dimming compositor over the real panels; panel snapshots,
  cached copies and duplicated panel render paths are forbidden.
- The standby compositor applies only a uniform dimming pass; no full-page beam is drawn.
- Button colors remain at the previous baseline until a separate palette decision is made.

1. The application uses the native Windows title bar and frame.
2. Search is parked until its final location is approved.
3. The workspace fills every available pixel at every window size.
4. The left panel contains working Library, Project and AI faces.
5. A Library category click opens the corresponding center thumbnail browser.
6. A thumbnail click selects the asset and updates Asset Inspector.
7. Only the Library, Project and AI tab headings switch the face.
8. No separate flip button is displayed.
9. The middle panel is Smart Workspace / Preview / Thumbnails.
10. The middle panel keeps its entrance and continuous active-preview animation.
11. The middle panel never participates in the Library/Projects flip.
12. The right panel is Asset Inspector and reflects thumbnail selection.
11. One continuous vertical gradient covers the whole interface: graphite at
    the top, dark through the middle and black toward the bottom.
12. No permanent divider or contour line is drawn between panels.
13. Panel surfaces are transparent and visually merge into the shared gradient.
14. A neutral moving light trace appears around the left panel only during
    hover/flip.
15. Main surfaces remain black, white and neutral gray. Blue is reserved for
    the standby logo.
16. The three-column desktop order is left, middle, right.
17. Below 820 px, the same semantic order becomes a vertical stack.
18. The interface must remain inside the viewport without horizontal or
    vertical overflow.
19. Print Screen remains unbound by Compass.
20. The prototype remains local-only and opens without authentication.
21. Search and Inspector interaction are disabled in standby.
22. Background controls stay disabled in standby; only the outer-ring hit area can wake the interface.
23. User activity resets the idle timer only while the active panel is visible.
24. Delivery files target Windows 10/11 x64 only.
