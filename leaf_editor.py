import math
import numpy as np
from PIL import Image
from OpenGL.GL import *
from OpenGL.GL import shaders
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from UI.SelectLeafGeneralDot import Ui_SelectLeafGeneralDot
from app_paths import get_path
from localization import LocalizationManager


class LeafGLCanvas(QOpenGLWidget):
    dot_changed = QtCore.pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tex_path = None
        self.tex_id = 0
        self.img_w = 256
        self.img_h = 256

        self.pan_offset = [0.0, 0.0]
        self.zoom = 1.0
        self.last_mouse = QtCore.QPoint()

        self.root_u = 0.5
        self.root_v = 0.0

        self.shader = None
        self.quad_vao = 0
        self.quad_vbo = 0

    def set_texture_path(self, path: str):
        self.tex_path = path
        if self.isValid():
            self._load_tex()
            self.update()

    def _load_tex(self):
        self.makeCurrent()
        if self.tex_id != 0:
            glDeleteTextures([self.tex_id])
            self.tex_id = 0

        if not self.tex_path:
            return

        try:
            im = Image.open(self.tex_path).convert("RGBA")
            self.img_w, self.img_h = im.size
            data = im.tobytes("raw", "RGBA", 0, -1)
            self.tex_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.tex_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.img_w, self.img_h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glBindTexture(GL_TEXTURE_2D, 0)
        except Exception as e:
            print(f"Ошибка загрузки текстуры листа: {e}")

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.12, 0.13, 0.15, 1.0)

        vs_path = get_path("shaders", "leaf_picker_vertex.glsl")
        fs_path = get_path("shaders", "leaf_picker_fragment.glsl")

        with open(vs_path, "r", encoding="utf-8") as f:
            vs_source = f.read()
        with open(fs_path, "r", encoding="utf-8") as f:
            fs_source = f.read()

        vs = shaders.compileShader(vs_source, GL_VERTEX_SHADER)
        fs = shaders.compileShader(fs_source, GL_FRAGMENT_SHADER)
        self.shader = shaders.compileProgram(vs, fs)

        self.quad_vao = glGenVertexArrays(1)
        self.quad_vbo = glGenBuffers(1)

        if self.tex_path:
            self._load_tex()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)
        if not self.shader:
            return
        glUseProgram(self.shader)

        w = self.width()
        h = self.height()

        left = -w * 0.5 * self.zoom - self.pan_offset[0]
        right = w * 0.5 * self.zoom - self.pan_offset[0]
        bottom = -h * 0.5 * self.zoom - self.pan_offset[1]
        top = h * 0.5 * self.zoom - self.pan_offset[1]

        ortho = np.array([
            [2.0 / (right - left), 0.0, 0.0, -(right + left) / (right - left)],
            [0.0, 2.0 / (top - bottom), 0.0, -(top + bottom) / (top - bottom)],
            [0.0, 0.0, -1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype=np.float32).T

        glUniformMatrix4fv(glGetUniformLocation(self.shader, "ortho"), 1, GL_FALSE, ortho)

        hw = self.img_w * 0.5
        hh = self.img_h * 0.5

        quad_verts = np.array([
            -hw, -hh, 0.0, 0.0,
             hw, -hh, 1.0, 0.0,
             hw,  hh, 1.0, 1.0,
            -hw, -hh, 0.0, 0.0,
             hw,  hh, 1.0, 1.0,
            -hw,  hh, 0.0, 1.0
        ], dtype=np.float32)

        glBindVertexArray(self.quad_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.quad_vbo)
        glBufferData(GL_ARRAY_BUFFER, quad_verts.nbytes, quad_verts, GL_DYNAMIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        glUniform1i(glGetUniformLocation(self.shader, "tex"), 0)
        glUniform1i(glGetUniformLocation(self.shader, "isTexture"), 1)
        glDrawArrays(GL_TRIANGLES, 0, 6)

        self._render_crosshair(hw, hh)

    def _render_crosshair(self, hw, hh):
        cx = -hw + self.root_u * (hw * 2.0)
        cy = -hh + self.root_v * (hh * 2.0)
        r = 16.0 * self.zoom

        lines = [
            cx - r * 1.5, cy, 0.0, 0.0,
            cx + r * 1.5, cy, 0.0, 0.0,
            cx, cy - r * 1.5, 0.0, 0.0,
            cx, cy + r * 1.5, 0.0, 0.0,
        ]
        segments = 32
        for i in range(segments):
            a1 = (i / segments) * 2.0 * math.pi
            a2 = ((i + 1) / segments) * 2.0 * math.pi
            lines.extend([
                cx + math.cos(a1) * r, cy + math.sin(a1) * r, 0.0, 0.0,
                cx + math.cos(a2) * r, cy + math.sin(a2) * r, 0.0, 0.0
            ])

        glLineWidth(1.0)
        line_arr = np.array(lines, dtype=np.float32)
        glBufferData(GL_ARRAY_BUFFER, line_arr.nbytes, line_arr, GL_DYNAMIC_DRAW)
        glUniform1i(glGetUniformLocation(self.shader, "isTexture"), 0)
        glUniform4f(glGetUniformLocation(self.shader, "drawColor"), 0.1, 0.95, 1.0, 1.0)
        glDrawArrays(GL_LINES, 0, len(lines) // 4)

    def mousePressEvent(self, event):
        self.last_mouse = event.pos()
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._pick_point(event.position().x(), event.position().y())

    def mouseMoveEvent(self, event):
        pos = event.pos()
        dx = pos.x() - self.last_mouse.x()
        dy = pos.y() - self.last_mouse.y()
        self.last_mouse = pos

        if event.buttons() & QtCore.Qt.MouseButton.MiddleButton:
            self.pan_offset[0] += dx * self.zoom
            self.pan_offset[1] -= dy * self.zoom
            self.update()
        elif event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._pick_point(event.position().x(), event.position().y())

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        scale = 0.9 if delta > 0 else 1.1
        self.zoom = float(np.clip(self.zoom * scale, 0.05, 20.0))
        self.update()

    def _pick_point(self, mouse_x, mouse_y):
        w = self.width()
        h = self.height()
        world_x = (mouse_x - w * 0.5) * self.zoom - self.pan_offset[0]
        world_y = ((h - mouse_y) - h * 0.5) * self.zoom - self.pan_offset[1]

        hw = self.img_w * 0.5
        hh = self.img_h * 0.5

        u = (world_x + hw) / (self.img_w if self.img_w > 0 else 1.0)
        v = (world_y + hh) / (self.img_h if self.img_h > 0 else 1.0)

        self.root_u = float(np.clip(u, 0.0, 1.0))
        self.root_v = float(np.clip(v, 0.0, 1.0))
        self.dot_changed.emit(self.root_u, self.root_v)
        self.update()


class SelectLeafDialog(QtWidgets.QMainWindow, Ui_SelectLeafGeneralDot):
    point_selected = QtCore.pyqtSignal(float, float)

    def __init__(self, texture_path: str, current_root=(0.5, 0.0), loc_mgr: LocalizationManager = None, parent=None):
        super().__init__(parent)
        self.loc_mgr = loc_mgr
        self.setupUi(self)

        parent_layout = self.rootLayout
        idx = parent_layout.indexOf(self.openGLWidget)
        self.openGLWidget.deleteLater()

        self.canvas = LeafGLCanvas(self.centralwidget)
        self.canvas.root_u, self.canvas.root_v = current_root
        self.canvas.set_texture_path(texture_path)
        parent_layout.insertWidget(idx, self.canvas, stretch=1)

        self.xpos.setRange(0.0, 1.0)
        self.xpos.setSingleStep(0.01)
        self.xpos.setDecimals(3)
        self.xpos.setValue(self.canvas.root_u)

        self.ypos.setRange(0.0, 1.0)
        self.ypos.setSingleStep(0.01)
        self.ypos.setDecimals(3)
        self.ypos.setValue(self.canvas.root_v)

        self.canvas.dot_changed.connect(self._on_canvas_pick)
        self.xpos.valueChanged.connect(self._on_spin_change)
        self.ypos.valueChanged.connect(self._on_spin_change)

        self.pushButton.clicked.connect(self.on_accept)
        self.pushButton_2.clicked.connect(self.close)

        self.apply_localization()

    def apply_localization(self):
        if not self.loc_mgr:
            return
        t = self.loc_mgr.tr
        self.setWindowTitle(t("leaf_dialog_title", "Выбрать корневую точку листочка"))
        self.label.setText(f"<html><head/><body><p align=\"center\">{t('leaf_dialog_header', 'Выбрать корневую точку<br/>листочка')}</p></body></html>")
        self.pushButton.setText(t("select", "Выбрать"))
        self.pushButton_2.setText(t("cancel", "Отмена"))

    def _on_canvas_pick(self, u, v):
        self.xpos.blockSignals(True)
        self.ypos.blockSignals(True)
        self.xpos.setValue(u)
        self.ypos.setValue(v)
        self.xpos.blockSignals(False)
        self.ypos.blockSignals(False)

    def _on_spin_change(self):
        self.canvas.root_u = float(self.xpos.value())
        self.canvas.root_v = float(self.ypos.value())
        self.canvas.update()

    def on_accept(self):
        self.point_selected.emit(float(self.xpos.value()), float(self.ypos.value()))
        self.close()