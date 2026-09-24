# Project structure — 0.6.4

```text
Artmach-Compass/
├── artmach_compass/
│   ├── core/
│   │   └── __init__.py
│   ├── ui/
│   │   ├── app_bar.py        Parked search component for its future location
│   │   ├── main_window.py    Native shell, gradient and responsive geometry
│   │   ├── workspace.py      Panels, navigation, preview and dashboard layout
│   │   └── theme.py          Shared achromatic transparent-panel visual system
│   └── app.py                QApplication entry point
├── installer/
│   └── ArtmachCompass.iss    Inno Setup installer definition
├── resources/
│   └── icons/
├── scripts/
│   ├── build_installer.ps1
│   ├── build_windows.ps1
│   └── run_source.ps1
├── tests/
│   └── test_project.py
├── Install_Prototype.cmd
├── main.py
├── requirements.txt
└── README.md
```

`CompassWorkspace.PANEL_ORDER` is the authoritative semantic mapping:
`library_projects`, `preview`, `asset_inspector`. The left panel owns the
Library/Projects flip. The center panel owns the live preview and does not react to the flip. Standby mode and orbit visuals were removed in 0.6.4.
