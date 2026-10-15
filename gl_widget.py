import ctypes
import numpy as np
import pyrr
from PIL import Image
from OpenGL.GL import *
from OpenGL.GL import shaders
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPoint
from app_paths import get_path


class TreeGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_dist = 22.0
        self.pitch = 18.0
        self.yaw = 45.0
        self.target = np.array([0.0, 5.0, 0.0], dtype=np.float32)
        self.last_mouse_pos = QPoint()

        self.wood_vao = 0
        self.wood_vbo = 0
        self.wood_count = 0

        self.leaf_vao = 0
        self.leaf_vbo = 0
        self.leaf_count = 0

        self.shader = None
        self.default_white_tex = 0
        self.default_normal_tex = 0

        self.wood_textures = {'albedo': 0, 'normal': 0, 'rough': 0, 'transmission': 0, 'ao': 0}
        self.leaf_textures = {'albedo': 0, 'normal': 0, 'rough': 0, 'transmission': 0, 'ao': 0}

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glFrontFace(GL_CCW)
        glClearColor(0.18, 0.20, 0.22, 1.0)

        vs_path = get_path("shaders", "tree_vertex.glsl")
        fs_path = get_path("shaders", "tree_fragment.glsl")

        with open(vs_path, "r", encoding="utf-8") as f:
            vs_source = f.read()
        with open(fs_path, "r", encoding="utf-8") as f:
            fs_source = f.read()

        vs = shaders.compileShader(vs_source, GL_VERTEX_SHADER)
        fs = shaders.compileShader(fs_source, GL_FRAGMENT_SHADER)
        self.shader = shaders.compileProgram(vs, fs)

        self.default_white_tex = self._create_solid_texture([220, 220, 220, 255])
        self.default_normal_tex = self._create_solid_texture([128, 128, 255, 255])

        self.wood_vao = glGenVertexArrays(1)
        self.wood_vbo = glGenBuffers(1)
        self.leaf_vao = glGenVertexArrays(1)
        self.leaf_vbo = glGenBuffers(1)

    def _create_solid_texture(self, rgba):
        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        data = np.array(rgba, dtype=np.uint8)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        return tex

    def load_texture(self, file_path):
        self.makeCurrent()
        try:
            img = Image.open(file_path).convert("RGBA")
            data = img.tobytes("raw", "RGBA", 0, -1)
            tex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            glGenerateMipmap(GL_TEXTURE_2D)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            return tex
        except Exception as e:
            print(f"Ошибка текстуры {file_path}: {e}")
            return 0

    def delete_gl_texture(self, tex_id):
        if tex_id != 0:
            self.makeCurrent()
            glDeleteTextures([tex_id])

    def set_wood_data(self, verts_array):
        self.makeCurrent()
        if self.wood_vao == 0:
            return
        self.wood_count = len(verts_array) // 11
        glBindVertexArray(self.wood_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.wood_vbo)
        glBufferData(GL_ARRAY_BUFFER, verts_array.nbytes, verts_array, GL_STATIC_DRAW)
        stride = 11 * 4
        for i in range(4):
            glEnableVertexAttribArray(i)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
        glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(32))
        glBindVertexArray(0)
        self.update()

    def set_leaf_data(self, verts_array):
        self.makeCurrent()
        if self.leaf_vao == 0:
            return
        self.leaf_count = len(verts_array) // 11
        glBindVertexArray(self.leaf_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.leaf_vbo)
        glBufferData(GL_ARRAY_BUFFER, verts_array.nbytes, verts_array, GL_STATIC_DRAW)
        stride = 11 * 4
        for i in range(4):
            glEnableVertexAttribArray(i)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
        glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(32))
        glBindVertexArray(0)
        self.update()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(self.shader)

        rad_p = np.radians(self.pitch)
        rad_y = np.radians(self.yaw)
        cx = self.target[0] + self.camera_dist * np.cos(rad_p) * np.sin(rad_y)
        cy = self.target[1] + self.camera_dist * np.sin(rad_p)
        cz = self.target[2] + self.camera_dist * np.cos(rad_p) * np.cos(rad_y)
        cam_pos = np.array([cx, cy, cz], dtype=np.float32)

        view = pyrr.matrix44.create_look_at(cam_pos, self.target, np.array([0, 1, 0], dtype=np.float32))
        aspect = self.width() / max(1, self.height())
        proj = pyrr.matrix44.create_perspective_projection_matrix(45.0, aspect, 0.1, 1000.0)
        model = pyrr.matrix44.create_identity()

        glUniformMatrix4fv(glGetUniformLocation(self.shader, "model"), 1, GL_FALSE, model.astype(np.float32))
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "view"), 1, GL_FALSE, view.astype(np.float32))
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "proj"), 1, GL_FALSE, proj.astype(np.float32))

        glUniform3fv(glGetUniformLocation(self.shader, "viewPos"), 1, cam_pos)
        glUniform3f(glGetUniformLocation(self.shader, "lightPos"), cx + 15.0, cy + 25.0, cz + 15.0)

        if self.wood_count > 0:
            self._bind_material(self.wood_textures)
            glBindVertexArray(self.wood_vao)
            glDrawArrays(GL_TRIANGLES, 0, self.wood_count)

        if self.leaf_count > 0:
            glDisable(GL_CULL_FACE)
            self._bind_material(self.leaf_textures)
            glBindVertexArray(self.leaf_vao)
            glDrawArrays(GL_TRIANGLES, 0, self.leaf_count)
            glEnable(GL_CULL_FACE)

    def _bind_material(self, tex_dict):
        def bind(tex_id, unit, name, default):
            glActiveTexture(GL_TEXTURE0 + unit)
            glBindTexture(GL_TEXTURE_2D, tex_id if tex_id != 0 else default)
            glUniform1i(glGetUniformLocation(self.shader, name), unit)

        bind(tex_dict['albedo'], 0, "texAlbedo", self.default_white_tex)
        bind(tex_dict['normal'], 1, "texNormal", self.default_normal_tex)
        bind(tex_dict['rough'], 2, "texRoughness", self.default_white_tex)
        bind(tex_dict['transmission'], 3, "texTransmission", self.default_white_tex)
        bind(tex_dict['ao'], 4, "texAO", self.default_white_tex)

        glUniform1i(glGetUniformLocation(self.shader, "hasAlbedo"), 1 if tex_dict['albedo'] != 0 else 0)
        glUniform1i(glGetUniformLocation(self.shader, "hasNormal"), 1 if tex_dict['normal'] != 0 else 0)
        glUniform1i(glGetUniformLocation(self.shader, "hasRoughness"), 1 if tex_dict['rough'] != 0 else 0)
        glUniform1i(glGetUniformLocation(self.shader, "hasTransmission"), 1 if tex_dict['transmission'] != 0 else 0)
        glUniform1i(glGetUniformLocation(self.shader, "hasAO"), 1 if tex_dict['ao'] != 0 else 0)

    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.position().x() - self.last_mouse_pos.x()
        dy = event.position().y() - self.last_mouse_pos.y()
        self.last_mouse_pos = event.pos()

        if event.buttons() & Qt.MouseButton.LeftButton:
            self.yaw -= dx * 0.4
            self.pitch = np.clip(self.pitch - dy * 0.4, -89.0, 89.0)
            self.update()
        elif event.buttons() & Qt.MouseButton.RightButton:
            self.target[1] += dy * 0.03
            self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self.camera_dist = max(1.0, self.camera_dist - delta * 2.0)
        self.update()