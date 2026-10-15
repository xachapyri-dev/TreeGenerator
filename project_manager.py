import os
import sys
import json
import shutil
import zipfile
import numpy as np


class ProjectManager:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.app_root = os.path.dirname(sys.executable)
        else:
            self.app_root = os.path.dirname(os.path.abspath(__file__))

        self.temp_root = os.path.join(self.app_root, "Temp")
        self.project_name = "none"
        self.project_file_path = None
        self.work_dir = os.path.join(self.temp_root, self.project_name)
        self.textures_dir = os.path.join(self.work_dir, "textures")

        self._init_workspace()

    def _init_workspace(self):
        os.makedirs(self.textures_dir, exist_ok=True)

    def set_project_name(self, new_name: str, wood_paths: dict = None, leaf_paths: dict = None):
        new_name = new_name.strip() or "none"
        old_work_dir = os.path.abspath(self.work_dir)
        new_work_dir = os.path.abspath(os.path.join(self.temp_root, new_name))

        if new_work_dir != old_work_dir:
            if os.path.exists(old_work_dir):
                if os.path.exists(new_work_dir):
                    shutil.rmtree(new_work_dir, ignore_errors=True)
                shutil.move(old_work_dir, new_work_dir)

            for paths_dict in (wood_paths, leaf_paths):
                if paths_dict:
                    for slot, p in list(paths_dict.items()):
                        if p:
                            abs_p = os.path.abspath(p)
                            if abs_p.startswith(old_work_dir):
                                rel = os.path.relpath(abs_p, old_work_dir)
                                paths_dict[slot] = os.path.join(new_work_dir, rel)

            self.project_name = new_name
            self.work_dir = new_work_dir
            self.textures_dir = os.path.join(self.work_dir, "textures")
            os.makedirs(self.textures_dir, exist_ok=True)

    def import_texture_to_workspace(self, src_path: str, target: str, slot: str) -> str:
        if not src_path or not os.path.exists(src_path):
            return None
        os.makedirs(self.textures_dir, exist_ok=True)

        ext = os.path.splitext(src_path)[1].lower()
        filename = f"{target}_{slot}{ext}"
        dst_path = os.path.join(self.textures_dir, filename)

        if os.path.abspath(src_path) != os.path.abspath(dst_path):
            shutil.copy2(src_path, dst_path)

        return dst_path

    def save_to_tgtree(
        self,
        tgtree_path: str,
        tree_seed: int,
        params: dict,
        leaf_root_dot: tuple,
        wood_texture_paths: dict,
        leaf_texture_paths: dict,
        trunk_v: np.ndarray,
        branch_v: np.ndarray,
        leaf_v: np.ndarray,
    ):
        proj_name = os.path.splitext(os.path.basename(tgtree_path))[0]
        self.set_project_name(proj_name, wood_texture_paths, leaf_texture_paths)
        self.project_file_path = tgtree_path
        os.makedirs(self.textures_dir, exist_ok=True)

        saved_wood_tex = {}
        saved_leaf_tex = {}
        files_to_pack = []

        for slot, path in wood_texture_paths.items():
            if path and os.path.exists(path):
                local_path = self.import_texture_to_workspace(path, "wood", slot)
                wood_texture_paths[slot] = local_path
                arc_rel = f"textures/{os.path.basename(local_path)}"
                saved_wood_tex[slot] = arc_rel
                files_to_pack.append((local_path, arc_rel))
            else:
                saved_wood_tex[slot] = None

        for slot, path in leaf_texture_paths.items():
            if path and os.path.exists(path):
                local_path = self.import_texture_to_workspace(path, "leaf", slot)
                leaf_texture_paths[slot] = local_path
                arc_rel = f"textures/{os.path.basename(local_path)}"
                saved_leaf_tex[slot] = arc_rel
                files_to_pack.append((local_path, arc_rel))
            else:
                saved_leaf_tex[slot] = None

        mesh_path = os.path.join(self.work_dir, "mesh_data.npz")
        np.savez_compressed(
            mesh_path,
            trunk_v=trunk_v,
            branch_v=branch_v,
            leaf_v=leaf_v,
        )

        project_data = {
            "version": "1.1",
            "project_name": self.project_name,
            "tree_seed": int(tree_seed),
            "params": params,
            "leaf_root_dot": [float(leaf_root_dot[0]), float(leaf_root_dot[1])],
            "wood_textures": saved_wood_tex,
            "leaf_textures": saved_leaf_tex,
        }
        json_path = os.path.join(self.work_dir, "project.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

        with zipfile.ZipFile(tgtree_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_path, "project.json")
            zf.write(mesh_path, "mesh_data.npz")
            for full_path, arc_name in files_to_pack:
                if os.path.exists(full_path):
                    zf.write(full_path, arc_name)

    def load_from_tgtree(self, tgtree_path: str) -> dict:
        proj_name = os.path.splitext(os.path.basename(tgtree_path))[0]
        self.project_name = proj_name
        self.project_file_path = tgtree_path
        self.work_dir = os.path.join(self.temp_root, self.project_name)
        self.textures_dir = os.path.join(self.work_dir, "textures")

        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir, ignore_errors=True)
        os.makedirs(self.textures_dir, exist_ok=True)

        with zipfile.ZipFile(tgtree_path, "r") as zf:
            zf.extractall(self.work_dir)

        json_path = os.path.join(self.work_dir, "project.json")
        mesh_path = os.path.join(self.work_dir, "mesh_data.npz")

        with open(json_path, "r", encoding="utf-8") as f:
            project_data = json.load(f)

        meshes = np.load(mesh_path)
        trunk_v = meshes["trunk_v"].astype(np.float32)
        branch_v = meshes["branch_v"].astype(np.float32)
        leaf_v = meshes["leaf_v"].astype(np.float32)

        wood_tex_abs = {}
        for slot in ['albedo', 'normal', 'rough', 'transmission', 'ao']:
            rel = project_data.get("wood_textures", {}).get(slot)
            if rel:
                abs_p = os.path.normpath(os.path.join(self.work_dir, rel))
                wood_tex_abs[slot] = abs_p if os.path.exists(abs_p) else None
            else:
                wood_tex_abs[slot] = None

        leaf_tex_abs = {}
        for slot in ['albedo', 'normal', 'rough', 'transmission', 'ao']:
            rel = project_data.get("leaf_textures", {}).get(slot)
            if rel:
                abs_p = os.path.normpath(os.path.join(self.work_dir, rel))
                leaf_tex_abs[slot] = abs_p if os.path.exists(abs_p) else None
            else:
                leaf_tex_abs[slot] = None

        loaded_params = project_data.get("params") or project_data.get("parameters", {})

        return {
            "tree_seed": int(project_data.get("tree_seed", 42)),
            "params": loaded_params,
            "leaf_root_dot": tuple(project_data.get("leaf_root_dot", [0.5, 0.0])),
            "wood_textures": wood_tex_abs,
            "leaf_textures": leaf_tex_abs,
            "trunk_v": trunk_v,
            "branch_v": branch_v,
            "leaf_v": leaf_v,
        }

    def cleanup_temp(self):
        if os.path.exists(self.temp_root):
            shutil.rmtree(self.temp_root, ignore_errors=True)