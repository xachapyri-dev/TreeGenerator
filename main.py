import os
import sys
import copy
import random
import ctypes
import inspect
import numpy as np
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtGui import QSurfaceFormat, QKeySequence, QShortcut
gl_format = QSurfaceFormat()
gl_format.setVersion(3, 3)
gl_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
gl_format.setDepthBufferSize(24)
QSurfaceFormat.setDefaultFormat(gl_format)
from UI.MainWindow import Ui_MainWindow
from gl_widget import TreeGLWidget
from generator import TreeMeshGenerator
from leaf_editor import SelectLeafDialog
from localization import LocalizationManager
from config_manager import load_settings, save_settings
from dialogs import FirstRunLanguageDialog, SettingsWindow
from app_paths import get_path
from project_manager import ProjectManager
from export import (
    export_to_obj,
    export_to_fbx,
    export_to_glb,
    export_to_unity_builtin,
    export_to_unity_urp,
    export_to_unity_hdrp,
)


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, settings: dict, loc_mgr: LocalizationManager):
        super().__init__()
        self.settings = settings
        self.loc_mgr = loc_mgr
        self.setupUi(self)

        self.proj_mgr = ProjectManager()
        self.is_dirty = False
        self._restoring_state = False
        self._slider_dragging = False

        self.tree_seed = random.randint(1, 999999999)

        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 30

        icon_path = get_path("favicon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        parent_layout = self.contentHorizontalLayout
        idx = parent_layout.indexOf(self.openGLWidget)
        self.openGLWidget.deleteLater()

        self.glView = TreeGLWidget(self.centralwidget)
        parent_layout.insertWidget(idx, self.glView, stretch=1)

        self._restoring_state = True
        self.horizontalSlider.setRange(1, 200)
        self.horizontalSlider.setValue(12)

        self.spinBox.setRange(3, 64)
        self.spinBox.setValue(16)

        self.spinBox_2.setRange(2, 60)
        self.spinBox_2.setValue(14)

        self.spinBox_3.setRange(0, 15)
        self.spinBox_3.setValue(4)

        self.spinBox_4.setRange(3, 32)
        self.spinBox_4.setValue(8)

        self.spinBox_5.setRange(10, 300)
        self.spinBox_5.setValue(35)
        self._restoring_state = False

        self.leaf_diffuse_path = None
        self.leaf_root_dot = (0.5, 0.0)

        self.wood_texture_paths = {'albedo': None, 'normal': None, 'rough': None, 'transmission': None, 'ao': None}
        self.leaf_texture_paths = {'albedo': None, 'normal': None, 'rough': None, 'transmission': None, 'ao': None}

        self.wood_labels = {
            'albedo': self.label,
            'normal': self.label_3,
            'rough': self.label_5,
            'transmission': self.label_7,
            'ao': self.label_9,
        }
        self.leaf_labels = {
            'albedo': self.label_18,
            'normal': self.label_16,
            'rough': self.label_17,
            'transmission': self.label_13,
            'ao': self.label_22,
        }

        self.trunk_v = np.array([], dtype=np.float32)
        self.branch_v = np.array([], dtype=np.float32)
        self.leaf_v = np.array([], dtype=np.float32)
        self.wood_v = np.array([], dtype=np.float32)

        self.leaf_dialog = None
        self.settings_win = None

        self._bind_events()
        self._setup_shortcuts()
        self.apply_localization()

        QtCore.QTimer.singleShot(150, self._initial_generate)

    def _initial_generate(self):
        self._rebuild_tree_mesh(reset_camera=True, record_history=False)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.undo_stack.append(self._capture_state())
        self.set_dirty(False)

    def _setup_shortcuts(self):
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.undo)

        self.shortcut_redo = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.shortcut_redo.activated.connect(self.redo)

        self.shortcut_redo_alt = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.shortcut_redo_alt.activated.connect(self.redo)

        self.action_tgtree.setShortcut(QKeySequence("Ctrl+S"))

    def _bind_events(self):
        self.horizontalSlider.sliderPressed.connect(self._on_slider_pressed)
        self.horizontalSlider.valueChanged.connect(self._on_slider_value_changed)
        self.horizontalSlider.sliderReleased.connect(self._on_slider_released)

        for sb in (self.spinBox, self.spinBox_2, self.spinBox_3, self.spinBox_4, self.spinBox_5):
            sb.valueChanged.connect(self._on_spinbox_changed)

        self.sel_tex_stvol.clicked.connect(lambda: self.select_tex('wood', 'albedo', self.label))
        self.sel_nor_stvol.clicked.connect(lambda: self.select_tex('wood', 'normal', self.label_3))
        self.sel_rou_stvol.clicked.connect(lambda: self.select_tex('wood', 'rough', self.label_5))
        self.sel_tran_stvol.clicked.connect(lambda: self.select_tex('wood', 'transmission', self.label_7))
        self.sel_ao_stvol.clicked.connect(lambda: self.select_tex('wood', 'ao', self.label_9))

        self.del_tex_stvol.clicked.connect(lambda: self.remove_tex('wood', 'albedo', self.label))
        self.del_nor_stvol.clicked.connect(lambda: self.remove_tex('wood', 'normal', self.label_3))
        self.del_rou_stvol.clicked.connect(lambda: self.remove_tex('wood', 'rough', self.label_5))
        self.del_tra_stvol.clicked.connect(lambda: self.remove_tex('wood', 'transmission', self.label_7))
        self.del_ao_stvol.clicked.connect(lambda: self.remove_tex('wood', 'ao', self.label_9))

        self.sel_tex_leaf.clicked.connect(lambda: self.select_tex('leaf', 'albedo', self.label_18, is_leaf_main=True))
        self.sel_nor_leaf.clicked.connect(lambda: self.select_tex('leaf', 'normal', self.label_16))
        self.sel_rou_leaf.clicked.connect(lambda: self.select_tex('leaf', 'rough', self.label_17))
        self.sel_tra_leaf.clicked.connect(lambda: self.select_tex('leaf', 'transmission', self.label_13))
        self.sel_ao_leaf.clicked.connect(lambda: self.select_tex('leaf', 'ao', self.label_22))

        self.del_tex_leaf.clicked.connect(lambda: self.remove_tex('leaf', 'albedo', self.label_18, is_leaf_main=True))
        self.del_nor_leaf.clicked.connect(lambda: self.remove_tex('leaf', 'normal', self.label_16))
        self.del_rou_leaf.clicked.connect(lambda: self.remove_tex('leaf', 'rough', self.label_17))
        self.del_tra_leaf.clicked.connect(lambda: self.remove_tex('leaf', 'transmission', self.label_13))
        self.del_ao_leaf.clicked.connect(lambda: self.remove_tex('leaf', 'ao', self.label_22))

        self.kor_dot_leaf.clicked.connect(self.open_leaf_dot_dialog)

        self.pushButton.clicked.connect(self.generate_new_tree)

        self.pushButton_12.clicked.connect(self.on_export_obj)
        self.pushButton_13.clicked.connect(self.on_export_fbx)

        if hasattr(self, 'exportGlb'):
            self.exportGlb.clicked.connect(self.on_export_glb)

        self.pushButton_27.clicked.connect(self.on_export_unity)
        self.pushButton_28.clicked.connect(self.on_export_unity_urp)
        self.pushButton_29.clicked.connect(self.on_export_unity_hdrp)

        self.action_tgtree.triggered.connect(self.save_project)
        self.action_tgtree_2.triggered.connect(self.load_project)
        self.action_2.triggered.connect(self.close)

        self.action_open_settings = QtGui.QAction(self)
        self.action_open_settings.triggered.connect(self.open_settings)
        self.menu_2.clear()
        self.menu_2.addAction(self.action_open_settings)


    def set_dirty(self, dirty: bool = True):
        self.is_dirty = dirty
        self.update_window_title()

    def update_window_title(self):
        t = self.loc_mgr.tr
        base_title = t("app_title", "Tree Generator")
        star = "*" if self.is_dirty else ""
        self.setWindowTitle(f"{base_title} - {self.proj_mgr.project_name}{star}")


    def _get_current_params(self) -> dict:
        return {
            "height": int(self.horizontalSlider.value()),
            "trunk_quality": int(self.spinBox.value()),
            "branch_count": int(self.spinBox_2.value()),
            "sub_branch_count": int(self.spinBox_3.value()),
            "branch_quality": int(self.spinBox_4.value()),
            "leaves_per_branch": int(self.spinBox_5.value()),
        }

    def _capture_state(self) -> dict:
        return {
            "tree_seed": int(self.tree_seed),
            "params": self._get_current_params(),
            "leaf_root_dot": tuple(self.leaf_root_dot),
            "wood_textures": copy.deepcopy(self.wood_texture_paths),
            "leaf_textures": copy.deepcopy(self.leaf_texture_paths),
            "trunk_v": self.trunk_v.copy(),
            "branch_v": self.branch_v.copy(),
            "leaf_v": self.leaf_v.copy(),
        }

    def _push_history(self):
        if self._restoring_state:
            return
        self.undo_stack.append(self._capture_state())
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.set_dirty(True)

    def _apply_state(self, state: dict):
        self._restoring_state = True
        try:
            self.tree_seed = int(state.get("tree_seed", self.tree_seed))
            params = state.get("params") or state.get("parameters", {})

            self.horizontalSlider.setValue(int(params.get("height", 12)))
            self.spinBox.setValue(int(params.get("trunk_quality", 16)))
            self.spinBox_2.setValue(int(params.get("branch_count", 14)))
            self.spinBox_3.setValue(int(params.get("sub_branch_count", 4)))
            self.spinBox_4.setValue(int(params.get("branch_quality", 8)))
            self.spinBox_5.setValue(int(params.get("leaves_per_branch", 35)))

            self.leaf_root_dot = tuple(state.get("leaf_root_dot", (0.5, 0.0)))

            self._restore_texture_set('wood', state.get("wood_textures", {}), self.wood_labels)
            self._restore_texture_set('leaf', state.get("leaf_textures", {}), self.leaf_labels)
            self.leaf_diffuse_path = self.leaf_texture_paths.get('albedo')

            self.trunk_v = state["trunk_v"].copy()
            self.branch_v = state["branch_v"].copy()
            self.leaf_v = state["leaf_v"].copy()
            self.wood_v = (
                np.concatenate([self.trunk_v, self.branch_v])
                if len(self.trunk_v) > 0
                else np.array([], dtype=np.float32)
            )

            h = float(self.horizontalSlider.value())
            self.glView.target[1] = h * 0.45
            self.glView.set_wood_data(self.wood_v)
            self.glView.set_leaf_data(self.leaf_v)
            self.glView.update()
            self._update_poly_labels()
        finally:
            self._restoring_state = False

    def _restore_texture_set(self, target: str, new_paths: dict, labels_dict: dict):
        current_paths = self.wood_texture_paths if target == 'wood' else self.leaf_texture_paths
        gl_dict = self.glView.wood_textures if target == 'wood' else self.glView.leaf_textures

        for slot, label_view in labels_dict.items():
            path = new_paths.get(slot)
            if path != current_paths.get(slot):
                self.glView.delete_gl_texture(gl_dict.get(slot, 0))
                if path and os.path.exists(path):
                    tex_id = self.glView.load_texture(path)
                    gl_dict[slot] = tex_id
                    current_paths[slot] = path
                    pix = QtGui.QPixmap(path)
                    label_view.setPixmap(pix.scaled(54, 54, QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding))
                else:
                    gl_dict[slot] = 0
                    current_paths[slot] = None
                    label_view.clear()
                    label_view.setText(self.loc_mgr.tr("no_texture", "Нет"))

    def undo(self):
        if len(self.undo_stack) <= 1:
            return
        current = self.undo_stack.pop()
        self.redo_stack.append(current)
        prev_state = self.undo_stack[-1]
        self._apply_state(prev_state)
        self.set_dirty(True)

    def redo(self):
        if not self.redo_stack:
            return
        next_state = self.redo_stack.pop()
        self.undo_stack.append(next_state)
        self._apply_state(next_state)
        self.set_dirty(True)

    def _on_slider_pressed(self):
        self._slider_dragging = True

    def _on_slider_value_changed(self, value):
        if self._restoring_state:
            return
        self.update_tree_settings(record_history=not self._slider_dragging)

    def _on_slider_released(self):
        if self._slider_dragging:
            self._slider_dragging = False
            self._push_history()

    def _on_spinbox_changed(self, value):
        if self._restoring_state:
            return
        self.update_tree_settings(record_history=True)

    def generate_new_tree(self):
        self.tree_seed = random.randint(1, 999999999)
        self._rebuild_tree_mesh(reset_camera=False, record_history=True)

    def update_tree_settings(self, record_history: bool = True):
        self._rebuild_tree_mesh(reset_camera=False, record_history=record_history)

    def _rebuild_tree_mesh(self, reset_camera: bool = False, record_history: bool = True):
        h = float(self.horizontalSlider.value())

        random.seed(self.tree_seed)
        np.random.seed(self.tree_seed % (2**32 - 1))

        gen_kwargs = dict(
            height=h,
            trunk_quality=int(self.spinBox.value()),
            branch_count=int(self.spinBox_2.value()),
            sub_branch_count=int(self.spinBox_3.value()),
            branch_quality=int(self.spinBox_4.value()),
            leaves_per_branch=int(self.spinBox_5.value()),
            leaf_root=self.leaf_root_dot,
        )

        sig = inspect.signature(TreeMeshGenerator.generate)
        if "seed" in sig.parameters:
            gen_kwargs["seed"] = self.tree_seed

        self.trunk_v, self.branch_v, self.leaf_v = TreeMeshGenerator.generate(**gen_kwargs)

        self.wood_v = (
            np.concatenate([self.trunk_v, self.branch_v])
            if len(self.trunk_v) > 0
            else np.array([], dtype=np.float32)
        )

        self.glView.target[1] = h * 0.45
        if reset_camera:
            self.glView.camera_dist = h * 1.8

        self.glView.set_wood_data(self.wood_v)
        self.glView.set_leaf_data(self.leaf_v)

        self._update_poly_labels()

        if record_history and not self._restoring_state:
            self._push_history()

    def select_tex(self, target: str, slot: str, label_view: QtWidgets.QLabel, is_leaf_main: bool = False):
        t = self.loc_mgr.tr
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            t("select_texture_title", "Выбрать текстуру"),
            "",
            t("images_filter", "Изображения (*.png *.jpg *.jpeg *.tga *.bmp)")
        )
        if path:
            local_path = self.proj_mgr.import_texture_to_workspace(path, target, slot)
            pix = QtGui.QPixmap(local_path)
            label_view.setPixmap(pix.scaled(54, 54, QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding))
            tex_id = self.glView.load_texture(local_path)

            if target == 'wood':
                self.glView.delete_gl_texture(self.glView.wood_textures[slot])
                self.glView.wood_textures[slot] = tex_id
                self.wood_texture_paths[slot] = local_path
            else:
                self.glView.delete_gl_texture(self.glView.leaf_textures[slot])
                self.glView.leaf_textures[slot] = tex_id
                self.leaf_texture_paths[slot] = local_path
                if is_leaf_main:
                    self.leaf_diffuse_path = local_path

            self.glView.update()
            self._push_history()

    def remove_tex(self, target: str, slot: str, label_view: QtWidgets.QLabel, is_leaf_main: bool = False):
        if target == 'wood':
            if self.wood_texture_paths[slot] is None:
                return
            self.glView.delete_gl_texture(self.glView.wood_textures[slot])
            self.glView.wood_textures[slot] = 0
            self.wood_texture_paths[slot] = None
        else:
            if self.leaf_texture_paths[slot] is None:
                return
            self.glView.delete_gl_texture(self.glView.leaf_textures[slot])
            self.glView.leaf_textures[slot] = 0
            self.leaf_texture_paths[slot] = None
            if is_leaf_main:
                self.leaf_diffuse_path = None

        label_view.clear()
        label_view.setText(self.loc_mgr.tr("no_texture", "Нет"))
        self.glView.update()
        self._push_history()

    def open_leaf_dot_dialog(self):
        t = self.loc_mgr.tr
        if not self.leaf_diffuse_path:
            QtWidgets.QMessageBox.warning(
                self,
                t("warning_title", "Внимание"),
                t("warn_select_leaf_tex", "Сначала выберите основную текстуру листка!")
            )
            return

        self.leaf_dialog = SelectLeafDialog(self.leaf_diffuse_path, self.leaf_root_dot, self.loc_mgr, self)
        self.leaf_dialog.point_selected.connect(self._on_root_dot_confirmed)
        self.leaf_dialog.show()

    def _on_root_dot_confirmed(self, u: float, v: float):
        self.leaf_root_dot = (float(u), float(v))
        self.update_tree_settings(record_history=True)

    def save_project(self) -> bool:
        t = self.loc_mgr.tr
        save_path = self.proj_mgr.project_file_path
        if not save_path:
            save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                t("save_tree", "Сохранить дерево (.tgtree)"),
                "MyTree.tgtree",
                "Tree Generator Project (*.tgtree)"
            )
            if not save_path:
                return False
            if not save_path.lower().endswith(".tgtree"):
                save_path += ".tgtree"

        try:
            self.proj_mgr.save_to_tgtree(
                tgtree_path=save_path,
                tree_seed=self.tree_seed,
                params=self._get_current_params(),
                leaf_root_dot=self.leaf_root_dot,
                wood_texture_paths=self.wood_texture_paths,
                leaf_texture_paths=self.leaf_texture_paths,
                trunk_v=self.trunk_v,
                branch_v=self.branch_v,
                leaf_v=self.leaf_v,
            )
            self.leaf_diffuse_path = self.leaf_texture_paths.get('albedo')
            self.set_dirty(False)
            return True
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                t("error_title", "Ошибка"),
                f"Не удалось сохранить проект:\n{e}"
            )
            return False

    def load_project(self):
        t = self.loc_mgr.tr
        if self.is_dirty:
            if not self._confirm_unsaved_changes():
                return

        load_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            t("load_tree", "Загрузить дерево (.tgtree)"),
            "",
            "Tree Generator Project (*.tgtree)"
        )
        if not load_path or not os.path.exists(load_path):
            return

        try:
            state = self.proj_mgr.load_from_tgtree(load_path)
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._apply_state(state)
            self.undo_stack.append(self._capture_state())
            self.set_dirty(False)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                t("error_title", "Ошибка"),
                f"Не удалось загрузить проект .tgtree:\n{e}"
            )

    def _confirm_unsaved_changes(self) -> bool:
        t = self.loc_mgr.tr
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle(t("unsaved_title", "Несохранённые изменения"))
        msg.setText(t("unsaved_text", "В проекте есть несохранённые изменения. Сохранить их перед выходом?"))
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)

        btn_save = msg.addButton(t("btn_save", "Сохранить"), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        btn_discard = msg.addButton(t("btn_exit_nosave", "Выйти"), QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = msg.addButton(t("btn_cancel", "Отмена"), QtWidgets.QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_save)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked == btn_save:
            return self.save_project()
        elif clicked == btn_discard:
            return True
        else:
            return False

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self.is_dirty:
            if not self._confirm_unsaved_changes():
                event.ignore()
                return

        self.proj_mgr.cleanup_temp()
        event.accept()

    def open_settings(self):
        if self.settings_win is None:
            self.settings_win = SettingsWindow(self.settings, self.loc_mgr, self)
            self.settings_win.settings_changed.connect(self._on_settings_updated)

        self.settings_win.show()
        self.settings_win.raise_()
        self.settings_win.activateWindow()

    def _on_settings_updated(self):
        save_settings(self.settings)
        self.apply_localization()
        if self.leaf_dialog:
            self.leaf_dialog.apply_localization()

    def apply_localization(self):
        t = self.loc_mgr.tr
        self.update_window_title()

        self.pushButton.setText(t("generate", "Генерировать"))
        self.tabWidget.setTabText(0, t("tab_generate", "Генерация"))
        self.tabWidget.setTabText(1, t("tab_settings", "Настройки"))
        self.tabWidget.setTabText(2, t("tab_import", "Импорт"))

        self.tabWidget_2.setTabText(0, t("tab_trunk", "Ствол"))
        self.tabWidget_2.setTabText(1, t("tab_branches", "Ветви"))
        self.tabWidget_2.setTabText(2, t("tab_leaves", "Листья"))

        self.label_2.setText(t("texture", "Текстура"))
        self.label_4.setText(t("normal_map", "Карта нормалей"))
        self.label_6.setText(t("roughness_map", "Карта шероховатости"))
        self.label_8.setText(t("transmission_map", "Карта светопропускания"))
        self.label_10.setText(t("ao_map", "Ambient Occlusion"))
        self.label_11.setText(t("height", "Высота (метры)"))
        self.label_12.setText(t("trunk_quality", "Качество ствола"))

        self.sel_tex_stvol.setText(t("select", "Выбрать"))
        self.del_tex_stvol.setText(t("delete", "Удалить"))
        self.sel_nor_stvol.setText(t("select", "Выбрать"))
        self.del_nor_stvol.setText(t("delete", "Удалить"))
        self.sel_rou_stvol.setText(t("select", "Выбрать"))
        self.del_rou_stvol.setText(t("delete", "Удалить"))
        self.sel_tran_stvol.setText(t("select", "Выбрать"))
        self.del_tra_stvol.setText(t("delete", "Удалить"))
        self.sel_ao_stvol.setText(t("select", "Выбрать"))
        self.del_ao_stvol.setText(t("delete", "Удалить"))

        self.label_24.setText(t("branches_from_trunk", "Кол-во веток от ствола"))
        self.label_25.setText(t("sub_branches", "Кол-во веточек от веток"))
        self.label_26.setText(t("detail", "Детализация"))

        self.label_21.setText(t("texture", "Текстура"))
        self.label_19.setText(t("normal_map", "Карта нормалей"))
        self.label_14.setText(t("roughness_map", "Карта шероховатости"))
        self.label_15.setText(t("transmission_map", "Карта светопропускания"))
        self.label_20.setText(t("ao_map", "Ambient Occlusion"))
        self.label_27.setText(t("leaves_per_branch", "Кол-во листьев на ветку"))

        self.sel_tex_leaf.setText(t("select", "Выбрать"))
        self.del_tex_leaf.setText(t("delete", "Удалить"))
        self.sel_nor_leaf.setText(t("select", "Выбрать"))
        self.del_nor_leaf.setText(t("delete", "Удалить"))
        self.sel_rou_leaf.setText(t("select", "Выбрать"))
        self.del_rou_leaf.setText(t("delete", "Удалить"))
        self.sel_tra_leaf.setText(t("select", "Выбрать"))
        self.del_tra_leaf.setText(t("delete", "Удалить"))
        self.sel_ao_leaf.setText(t("select", "Выбрать"))
        self.del_ao_leaf.setText(t("delete", "Удалить"))
        self.kor_dot_leaf.setText(t("leaf_root_dot", "Корневая точка листочка"))

        self.pushButton_12.setText(t("export_obj", "Экспорт в OBJ"))
        self.pushButton_13.setText(t("export_fbx", "Экспорт в FBX"))
        if hasattr(self, 'exportGlb'):
            self.exportGlb.setText(t("export_glb", "Экспорт в GLB"))
        self.pushButton_27.setText(t("export_builtin", "Экспорт в Unity Built-in"))
        self.pushButton_28.setText(t("export_urp", "Экспорт в Unity URP"))
        self.pushButton_29.setText(t("export_hdrp", "Экспорт в Unity HDRP"))

        self.menu.setTitle(t("menu_file", "Файл"))
        self.menu_2.setTitle(t("menu_settings", "Настройки"))
        self.action_open_settings.setText(t("menu_settings", "Настройки"))
        self.action_tgtree.setText(t("save_tree", "Сохранить дерево (.tgtree)"))
        self.action_tgtree_2.setText(t("load_tree", "Загрузить дерево (.tgtree)"))
        self.action_2.setText(t("exit", "Выход"))

        self._update_poly_labels()


    def _update_poly_labels(self):
        t = self.loc_mgr.tr
        trunk_poly = len(self.trunk_v) // 33
        branch_poly = len(self.branch_v) // 33
        leaf_poly = len(self.leaf_v) // 33
        total_poly = trunk_poly + branch_poly + leaf_poly

        self.label_54.setText(f"{t('poly_trunk', 'Кол-во полигонов ствола: ')} {trunk_poly}")
        self.label_55.setText(f"{t('poly_branches', 'Кол-во полигонов веток: ')} {branch_poly}")
        self.label_53.setText(f"{t('poly_leaves', 'Кол-во полигонов листьев: ')} {leaf_poly}")
        self.label_56.setText(f"{t('poly_total', 'Общее кол-во полигонов: ')} {total_poly}")

    def _prompt_export_folder_and_name(self):
        t = self.loc_mgr.tr
        if len(self.wood_v) == 0 and len(self.leaf_v) == 0:
            QtWidgets.QMessageBox.warning(self, t("warning_title", "Внимание"), t("warn_empty_tree", "Сначала сгенерируйте дерево!"))
            return None, None

        parent_dir = QtWidgets.QFileDialog.getExistingDirectory(self, t("export_folder_title", "Выберите папку для экспорта"))
        if not parent_dir:
            return None, None

        model_name, ok = QtWidgets.QInputDialog.getText(
            self,
            t("export_name_prompt_title", "Имя модели"),
            t("export_name_prompt_label", "Введите название папки и модели:"),
            text="Tree_Model"
        )
        if not ok or not model_name.strip():
            return None, None

        model_name = model_name.strip().replace(" ", "_")
        target_dir = os.path.join(parent_dir, model_name)
        return target_dir, model_name

    def on_export_obj(self):
        target_dir, model_name = self._prompt_export_folder_and_name()
        if not target_dir:
            return

        export_to_obj(target_dir, model_name, self.wood_v, self.leaf_v, self.wood_texture_paths, self.leaf_texture_paths)

        t = self.loc_mgr.tr
        QtWidgets.QMessageBox.information(
            self,
            t("success_title", "Успех"),
            f"{t('export_success', 'Дерево успешно сохранено в формате .OBJ!')}\n{target_dir}"
        )

    def on_export_fbx(self):
        target_dir, model_name = self._prompt_export_folder_and_name()
        if not target_dir:
            return

        export_to_fbx(target_dir, model_name, self.wood_v, self.leaf_v, self.wood_texture_paths, self.leaf_texture_paths)

        t = self.loc_mgr.tr
        QtWidgets.QMessageBox.information(
            self,
            t("success_title", "Успех"),
            f"{t('export_fbx_success', 'Дерево успешно сохранено в формате .FBX!')}\n{target_dir}"
        )

    def on_export_glb(self):
        target_dir, model_name = self._prompt_export_folder_and_name()
        if not target_dir:
            return

        export_to_glb(
            target_dir,
            model_name,
            self.wood_v,
            self.leaf_v,
            self.wood_texture_paths,
            self.leaf_texture_paths,
        )

        t = self.loc_mgr.tr
        QtWidgets.QMessageBox.information(
            self,
            t("success_title", "Успех"),
            f"{t('export_glb_success', 'Дерево успешно сохранено в формате .GLB!')}\n{target_dir}"
        )

    def on_export_unity(self):
        t = self.loc_mgr.tr
        if len(self.wood_v) == 0 and len(self.leaf_v) == 0:
            QtWidgets.QMessageBox.warning(self, t("warning_title", "Внимание"), t("warn_empty_tree", "Сначала сгенерируйте дерево!"))
            return

        target_dir, model_name = self._prompt_export_folder_and_name()
        if not target_dir:
            return

        export_to_unity_builtin(
            target_dir,
            model_name,
            self.wood_v,
            self.leaf_v,
            self.wood_texture_paths,
            self.leaf_texture_paths
        )

        QtWidgets.QMessageBox.information(
            self,
            t("success_title", "Успех"),
            f"{t('export_unity_success', 'Ассет дерева успешно экспортирован для Unity!')}\n{target_dir}"
        )
    def on_export_unity_urp(self):
        t = self.loc_mgr.tr
        if len(self.wood_v) == 0 and len(self.leaf_v) == 0:
            QtWidgets.QMessageBox.warning(
                self, t("warning_title", "Внимание"), t("warn_empty_tree", "Сначала сгенерируйте дерево!")
            )
            return

        target_dir, model_name = self._prompt_export_folder_and_name()
        if not target_dir:
            return

        export_to_unity_urp(
            target_dir,
            model_name,
            self.wood_v,
            self.leaf_v,
            self.wood_texture_paths,
            self.leaf_texture_paths,
        )

        QtWidgets.QMessageBox.information(
            self,
            t("success_title", "Успех"),
            f"{t('export_unity_urp_success', 'Ассет дерева успешно экспортирован для Unity URP!')}\n{target_dir}",
        )

    def on_export_unity_hdrp(self):
        t = self.loc_mgr.tr
        if len(self.wood_v) == 0 and len(self.leaf_v) == 0:
            QtWidgets.QMessageBox.warning(
                self, t("warning_title", "Внимание"), t("warn_empty_tree", "Сначала сгенерируйте дерево!")
            )
            return

        target_dir, model_name = self._prompt_export_folder_and_name()
        if not target_dir:
            return

        export_to_unity_hdrp(
            target_dir,
            model_name,
            self.wood_v,
            self.leaf_v,
            self.wood_texture_paths,
            self.leaf_texture_paths,
        )

        QtWidgets.QMessageBox.information(
            self,
            t("success_title", "Успех"),
            f"{t('export_unity_hdrp_success', 'Ассет дерева успешно экспортирован для Unity HDRP!')}\n{target_dir}",
        )


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        try:
            myappid = 'treegenerator.app.v1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QtWidgets.QApplication(sys.argv)
    app.setDesktopFileName("treegenerator")

    icon_path = get_path("favicon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QtGui.QIcon(icon_path))

    loc_mgr = LocalizationManager()
    settings = load_settings()

    if settings.get("first_run", True):
        lang_dlg = FirstRunLanguageDialog(loc_mgr)
        if lang_dlg.exec():
            selected_lang = lang_dlg.get_selected_language()
            settings["language"] = selected_lang
            loc_mgr.set_language(selected_lang)
        settings["first_run"] = False
        save_settings(settings)
    else:
        loc_mgr.set_language(settings.get("language", "ru"))

    window = MainWindow(settings, loc_mgr)
    window.show()
    sys.exit(app.exec())