from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QColor, QVector3D
from PySide6.QtWidgets import QVBoxLayout, QWidget

from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender

from artmach_compass.core.app_logging import get_logger


class Model3DViewer(QWidget):
    """Interactive Qt3D viewport that renders an actual GLB scene.

    This replaces the previous behaviour where the "ANA 3D VIEWER" panel only
    ever painted a flat 2D thumbnail image (see PreviewCanvas). When a
    ``<asset>_preview.glb`` file exists, CenterWorkspacePanel loads it here
    instead of falling back to the static JPEG snapshot.
    """

    model_loaded = Signal(str)
    model_failed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("model3DViewer")

        self._window = Qt3DExtras.Qt3DWindow()
        self._window.defaultFrameGraph().setClearColor(QColor(24, 27, 34))

        container = QWidget.createWindowContainer(self._window, self)
        container.setMinimumSize(160, 120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(container)

        self._current_path = ""
        self._root_entity: Qt3DCore.QEntity | None = None
        self._model_entity: Qt3DCore.QEntity | None = None
        self._scene_loader: Qt3DRender.QSceneLoader | None = None
        self._build_scene()

    def _build_scene(self) -> None:
        self._root_entity = Qt3DCore.QEntity()

        camera = self._window.camera()
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 5000.0)
        camera.setPosition(QVector3D(0.0, 4.0, 12.0))
        camera.setViewCenter(QVector3D(0.0, 0.0, 0.0))
        camera.setUpVector(QVector3D(0.0, 1.0, 0.0))
        self._camera = camera

        light_entity = Qt3DCore.QEntity(self._root_entity)
        light = Qt3DRender.QPointLight(light_entity)
        light.setColor(QColor("white"))
        light.setIntensity(1.0)
        light_transform = Qt3DCore.QTransform(light_entity)
        light_transform.setTranslation(QVector3D(0.0, 8.0, 12.0))
        light_entity.addComponent(light)
        light_entity.addComponent(light_transform)

        # Left-drag orbits, wheel zooms, right-drag pans - standard Qt3D defaults.
        controller = Qt3DExtras.QOrbitCameraController(self._root_entity)
        controller.setLinearSpeed(80.0)
        controller.setLookSpeed(180.0)
        controller.setCamera(camera)
        self._controller = controller

        self._model_entity = Qt3DCore.QEntity(self._root_entity)
        self._scene_loader = Qt3DRender.QSceneLoader(self._model_entity)
        self._scene_loader.statusChanged.connect(self._on_status_changed)
        self._model_entity.addComponent(self._scene_loader)

        self._window.setRootEntity(self._root_entity)

    def _on_status_changed(self, status) -> None:
        ready = getattr(Qt3DRender.QSceneLoader.Status, "Ready", None)
        error = getattr(Qt3DRender.QSceneLoader.Status, "Error", None)
        get_logger().info(
            "Model3DViewer: scene status changed to %s for %s", status, self._current_path
        )
        if status == ready:
            self.model_loaded.emit(self._current_path)
        elif status == error:
            get_logger().error(
                "Model3DViewer: QSceneLoader reported Error status while loading %s. "
                "This is almost always a missing/failed Qt3D glTF import plugin in the "
                "frozen build - check for accompanying 'Qt: ...' warnings just above this "
                "line in the log.",
                self._current_path,
            )
            self.model_failed.emit(self._current_path)

    def load_model(self, glb_path: str) -> bool:
        """Point the scene loader at a .glb file. Returns False if it's missing."""
        path = Path(glb_path)
        self._current_path = str(path)
        get_logger().info("Model3DViewer: loading GLB %s", path)
        if not path.is_file():
            get_logger().error("Model3DViewer: GLB file does not exist: %s", path)
            self._scene_loader.setSource(QUrl())
            self.model_failed.emit(str(path))
            return False
        # Reset camera to a sane default each time a new model loads, since we
        # don't compute the scene's bounding box to auto-frame it.
        self._camera.setPosition(QVector3D(0.0, 4.0, 12.0))
        self._camera.setViewCenter(QVector3D(0.0, 0.0, 0.0))
        self._scene_loader.setSource(QUrl.fromLocalFile(str(path)))
        return True

    def clear(self) -> None:
        self._current_path = ""
        if self._scene_loader is not None:
            self._scene_loader.setSource(QUrl())
