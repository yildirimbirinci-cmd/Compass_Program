"""Achromatic, full-bleed visual system for the Compass prototype."""

APP_STYLESHEET = r"""
QWidget {
    background: transparent;
    color: #c8c8c8;
    font-family: "Segoe UI Variable", "Segoe UI";
    font-size: 12px;
}
QMainWindow {
    background: #010101;
}
QLabel {
    background: transparent;
}

/* The three panels expose the same parent gradient. */
QWidget#workspaceDeck,
QFrame#leftFlipPanel,
QFrame#animatedCenterPanel,
QFrame#centerPanelContent,
QWidget#previewCanvas,
QWidget#orbitBackdrop,
QWidget#standbyLogoPanel,
QStackedWidget#centerContentStack,
QWidget#thumbnailBrowser,
QScrollArea#thumbnailScroll,
QWidget#thumbnailViewport,
QFrame#libraryFace,
QFrame#projectsFace,
QFrame#aiFace,
QFrame#rightInspectorPanel,
QFrame#flipPanelFace {
    background: transparent;
    border: 0;
}

QLabel#panelEyebrow {
    color: #8b8b8b;
    font-size: 10px;
    font-weight: 700;
}
QLabel#panelHeading {
    color: #eeeeee;
    font-size: 24px;
    font-weight: 600;
}
QLabel#centerHeading {
    color: #f1f1f1;
    font-size: 28px;
    font-weight: 600;
}
QLabel#panelSubtitle {
    color: #989898;
    font-size: 11px;
}
QLabel#panelFooter {
    color: #707070;
    font-size: 9px;
    padding-top: 8px;
}
QLabel#liveStatus {
    color: #d6d6d6;
    background: rgba(98, 98, 98, 42);
    border: 1px solid rgba(166, 166, 166, 68);
    border-radius: 7px;
    font-size: 9px;
    font-weight: 700;
    padding: 3px 8px;
}

QFrame#navigationRow {
    background: rgba(255, 255, 255, 7);
    border: 0;
    border-radius: 8px;
}
QFrame#navigationRow:hover {
    background: rgba(255, 255, 255, 13);
}
QFrame#navigationRow[active="true"] {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 18),
        stop:1 rgba(255, 255, 255, 9)
    );
    border: 0;
}
QFrame#navigationMarker {
    background: #686868;
    border: 0;
    border-radius: 2px;
}
QFrame#navigationMarker[active="true"] {
    background: #47a6ff;
}
QFrame#navigationMarker[hovered="true"] {
    background: #ff8422;
}
QLabel#navigationTitle {
    color: #718aa4;
    font-size: 11px;
}
QLabel#navigationTitle[active="true"] {
    color: #58adff;
}
QLabel#navigationTitle[hovered="true"] {
    color: #ff8422;
}
QLabel#navigationDetail {
    color: #7d7d7d;
    font-size: 9px;
    font-weight: 600;
}

QFrame#assetThumbnailCard {
    background: rgba(255, 255, 255, 7);
    border: 1px solid rgba(255, 255, 255, 12);
    border-radius: 11px;
}
QFrame#assetThumbnailCard:hover {
    background: rgba(255, 255, 255, 13);
    border-color: rgba(255, 255, 255, 28);
}
QFrame#assetThumbnailCard[interactive="false"]:hover {
    background: rgba(255, 255, 255, 7);
    border-color: rgba(255, 255, 255, 12);
}
QFrame#assetThumbnailCard[selected="true"] {
    background: rgba(255, 255, 255, 19);
    border-color: rgba(226, 226, 226, 74);
}
QLabel#thumbnailTitle {
    color: #d8d8d8;
    font-size: 11px;
    font-weight: 600;
}
QLabel#thumbnailMeta {
    color: #797979;
    font-size: 9px;
}

QFrame#inspectorField {
    background: rgba(255, 255, 255, 7);
    border: 0;
    border-radius: 7px;
}
QLabel#inspectorKey {
    color: #858585;
    font-size: 9px;
    font-weight: 700;
}
QLabel#inspectorValue {
    color: #c9c9c9;
    font-size: 10px;
}
QProgressBar#cacheProgress {
    background: rgba(255, 255, 255, 12);
    border: 0;
    border-radius: 2px;
}
QProgressBar#cacheProgress::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #777777,
        stop:1 #d1d1d1
    );
    border-radius: 2px;
}
QFrame#activityCard {
    background: rgba(255, 255, 255, 9);
    border: 0;
    border-radius: 8px;
}
QLabel#activityText {
    color: #a2a2a2;
    font-size: 10px;
}

QToolButton,
QPushButton {
    font-size: 14px;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #303030,
        stop:1 #202020
    );
    color: #cccccc;
    border: 1px solid #3e3e3e;
    border-radius: 4px;
    padding: 5px 9px;
}
QToolButton:hover,
QPushButton:hover {
    background: #383838;
    border-color: #5d5d5d;
    color: #ffffff;
}
QToolButton:pressed,
QPushButton:pressed,
QToolButton:checked,
QPushButton:checked {
    background: #464646;
    border-color: #747474;
    color: #ffffff;
}

QScrollBar:vertical,
QScrollBar:horizontal {
    background: transparent;
    border: none;
    margin: 0;
}
QScrollBar:vertical {
    width: 12px;
}
QScrollBar:horizontal {
    height: 12px;
}
QScrollBar::groove:vertical,
QScrollBar::groove:horizontal {
    background: transparent;
    border: none;
}
QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
    background: rgba(172, 76, 12, 190);
    border: none;
    border-radius: 2px;
}
QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover,
QScrollBar::handle:vertical:pressed,
QScrollBar::handle:horizontal:pressed {
    background: rgba(255, 132, 34, 240);
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    width: 0;
    height: 0;
    background: transparent;
    border: none;
}

"""

# Production dashboard shell additions (0.4.9 layout pass)
APP_STYLESHEET += r"""
QFrame#topCommandBar {
    background: rgba(6, 10, 13, 246);
    border-bottom: 1px solid #20272d;
}
QFrame#workspaceBody {
    background: rgba(3, 6, 8, 232);
}
QFrame#bottomStatusBar {
    background: rgba(8, 13, 16, 250);
    border-top: 1px solid #242b30;
}
QFrame#brandBlock {
    background: transparent;
    border-right: 1px solid #242b30;
}
QLabel#brandMark {
    color: #ff8a00;
    font-size: 27px;
    font-weight: 700;
}
QLabel#brandTitle {
    color: #f4f4f4;
    font-size: 22px;
    font-weight: 800;
}
QLabel#brandSubtitle {
    color: #9a9fa3;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 1px;
}
QPushButton#topModeButton {
    background: rgba(255, 255, 255, 2);
    border: 0;
    border-right: 1px solid #20272d;
    border-radius: 5px;
    color: #d7d9db;
    padding: 5px 12px;
    text-align: left;
    font-size: 12px;
}
QPushButton#topModeButton:hover {
    background: rgba(255, 255, 255, 7);
    border-color: #30383e;
}
QPushButton#topModeButton[active="true"] {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(22,28,32,235), stop:1 rgba(11,15,18,245));
    border-bottom: 2px solid #47a6ff;
    color: #ffffff;
}
QLineEdit#globalSearch {
    background: #11171b;
    border: 1px solid #384149;
    border-radius: 7px;
    color: #e2e4e5;
    padding: 0 14px;
    selection-background-color: #9b5700;
}
QLineEdit#globalSearch:focus {
    border-color: #d87700;
}
QToolButton#commandButton,
QPushButton#profileButton {
    background: transparent;
    border: 0;
    border-left: 1px solid #20272d;
    border-radius: 0;
    color: #d9dcde;
    padding: 6px 12px;
}
QToolButton#commandButton,
QPushButton#profileButton {
    font-size: 14px;
}
QToolButton#commandButton:hover,
QPushButton#profileButton:hover {
    background: rgba(255,255,255,8);
    color: #ffffff;
}
QLabel#statusOk {
    color: #aeb7bd;
    font-size: 9px;
}
QLabel#statusText {
    color: #80898f;
    font-size: 9px;
}
QFrame#leftFlipPanel,
QFrame#animatedCenterPanel,
QFrame#rightInspectorPanel {
    background: rgba(10, 15, 18, 218);
    border: 1px solid #252d32;
    border-radius: 7px;
}
QFrame#animatedCenterPanel {
    background: rgba(8, 13, 16, 225);
}
QFrame#navigationRow {
    background: rgba(255, 255, 255, 4);
    border: 0;
    border-radius: 4px;
}
QFrame#navigationRow:hover {
    background: rgba(255, 255, 255, 9);
}
QFrame#navigationRow[active="true"] {
    /* Keep the same neutral button surface; the animated blue outline/glow is
       painted by NavigationRow.paintEvent. */
    background: rgba(255, 255, 255, 4);
    border: 0;
}
QFrame#navigationMarker[active="true"] {
    background: #47a6ff;
}
QLabel#navigationTitle {
    color: #c1c7cb;
    font-size: 12px;
}
QLabel#navigationTitle[active="true"] {
    color: #58adff;
}
QFrame#assetThumbnailCard {
    background: rgba(15, 21, 25, 230);
    border: 1px solid #283138;
    border-radius: 6px;
}
QFrame#assetThumbnailCard:hover {
    background: rgba(21, 28, 33, 240);
    border-color: #59636b;
}
QFrame#assetThumbnailCard[selected="true"] {
    background: rgba(21, 27, 30, 250);
    border-color: #47a6ff;
}
QFrame#inspectorField,
QFrame#activityCard {
    background: rgba(15, 21, 25, 220);
    border: 1px solid #283138;
    border-radius: 5px;
}

/* 0.5.4 fixed center panel composition */
QFrame#centerSubPanel, QFrame#assetPreviewDetailPanel {
    background: rgba(12, 17, 20, 235);
    border: 1px solid rgba(77, 96, 106, 150);
    border-radius: 8px;
}
QLabel#assetDetailPreview {
    background: rgba(7, 11, 14, 230);
    border: 1px solid rgba(62, 76, 84, 130);
    border-radius: 6px;
    color: rgba(150, 168, 180, 180);
}
QFrame#assetDetailFields {
    background: transparent;
    border: 0;
}
"""

APP_STYLESHEET += r"""
/* 0.5.4 brand and persistent scrollbar states */
QLabel#brandVersion {
    color: rgba(255, 132, 34, 190);
    font-size: 11px;
    font-weight: 600;
    padding-left: 0;
    padding-bottom: 1px;
}
QFrame#brandBlock {
    margin-left: 0;
    padding-left: 0;
}
"""

APP_STYLESHEET += r"""
QPushButton#generatePreviewButton {
    min-height: 34px;
    border: 1px solid rgba(218, 133, 53, 165);
    border-radius: 4px;
    background: rgba(40, 31, 24, 205);
    color: rgba(239, 170, 92, 235);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}
QPushButton#generatePreviewButton:hover {
    background: rgba(57, 39, 25, 225);
    border-color: rgba(239, 160, 75, 220);
}
QPushButton#generatePreviewButton:disabled {
    color: rgba(150, 150, 150, 120);
    border-color: rgba(110, 110, 110, 80);
    background: rgba(30, 30, 30, 120);
}
QLabel#previewGenerationStatus {
    color: rgba(160, 175, 192, 210);
    font-size: 9px;
}
QProgressBar#previewGenerationProgress {
    border: 0;
    background: rgba(255, 255, 255, 18);
}
QProgressBar#previewGenerationProgress::chunk {
    background: rgba(224, 139, 55, 220);
}

"""
