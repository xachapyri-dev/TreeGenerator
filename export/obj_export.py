import os
import shutil

def export_to_obj(target_dir: str, model_name: str, wood_v, leaf_v, wood_texture_paths: dict, leaf_texture_paths: dict) -> str:
    os.makedirs(target_dir, exist_ok=True)
    obj_file_path = os.path.join(target_dir, f"{model_name}.obj")
    mtl_file_path = os.path.join(target_dir, f"{model_name}.mtl")

    def copy_textures(paths_dict, prefix):
        saved = {}
        for slot, src in paths_dict.items():
            if src and os.path.exists(src):
                ext = os.path.splitext(src)[1]
                dst_name = f"{model_name}_{prefix}_{slot.capitalize()}{ext}"
                shutil.copy2(src, os.path.join(target_dir, dst_name))
                saved[slot] = dst_name
        return saved

    wood_copied = copy_textures(wood_texture_paths, "Wood")
    leaf_copied = copy_textures(leaf_texture_paths, "Leaf")

    with open(mtl_file_path, "w", encoding="utf-8") as mtl:
        mtl.write(f"# Materials for {model_name}\n\n")

        mtl.write("newmtl Material_Wood\n")
        mtl.write("Ka 0.2 0.2 0.2\nKd 0.8 0.8 0.8\nKs 0.2 0.2 0.2\nd 1.0\nillum 2\n")
        if 'albedo' in wood_copied:
            mtl.write(f"map_Kd {wood_copied['albedo']}\n")
        if 'normal' in wood_copied:
            mtl.write(f"bump {wood_copied['normal']}\nmap_bump {wood_copied['normal']}\n")
        if 'rough' in wood_copied:
            mtl.write(f"map_Ns {wood_copied['rough']}\n")

        mtl.write("\n")

        mtl.write("newmtl Material_Leaves\n")
        mtl.write("Ka 0.25 0.25 0.25\nKd 0.85 0.85 0.85\nKs 0.2 0.2 0.2\nd 1.0\nillum 2\n")
        if 'albedo' in leaf_copied:
            mtl.write(f"map_Kd {leaf_copied['albedo']}\nmap_d {leaf_copied['albedo']}\n")
        if 'normal' in leaf_copied:
            mtl.write(f"bump {leaf_copied['normal']}\nmap_bump {leaf_copied['normal']}\n")
        if 'rough' in leaf_copied:
            mtl.write(f"map_Ns {leaf_copied['rough']}\n")

    with open(obj_file_path, "w", encoding="utf-8") as obj:
        obj.write("# TreeGenerator Export\n")
        obj.write(f"mtllib {model_name}.mtl\n\n")

        w_count = len(wood_v) // 11
        l_count = len(leaf_v) // 11

        for i in range(w_count):
            idx = i * 11
            obj.write(f"v {wood_v[idx]:.4f} {wood_v[idx+1]:.4f} {wood_v[idx+2]:.4f}\n")
        for i in range(l_count):
            idx = i * 11
            obj.write(f"v {leaf_v[idx]:.4f} {leaf_v[idx+1]:.4f} {leaf_v[idx+2]:.4f}\n")

        for i in range(w_count):
            idx = i * 11
            obj.write(f"vt {wood_v[idx+6]:.4f} {wood_v[idx+7]:.4f}\n")
        for i in range(l_count):
            idx = i * 11
            obj.write(f"vt {leaf_v[idx+6]:.4f} {leaf_v[idx+7]:.4f}\n")

        for i in range(w_count):
            idx = i * 11
            obj.write(f"vn {wood_v[idx+3]:.4f} {wood_v[idx+4]:.4f} {wood_v[idx+5]:.4f}\n")
        for i in range(l_count):
            idx = i * 11
            obj.write(f"vn {leaf_v[idx+3]:.4f} {leaf_v[idx+4]:.4f} {leaf_v[idx+5]:.4f}\n")

        if w_count > 0:
            obj.write(f"\no {model_name}_Trunk\nusemtl Material_Wood\ns 1\n")
            for i in range(1, w_count + 1, 3):
                obj.write(f"f {i}/{i}/{i} {i+1}/{i+1}/{i+1} {i+2}/{i+2}/{i+2}\n")

        if l_count > 0:
            obj.write(f"\no {model_name}_Leaves\nusemtl Material_Leaves\ns off\n")
            base = w_count
            for i in range(base + 1, base + l_count + 1, 3):
                obj.write(f"f {i}/{i}/{i} {i+1}/{i+1}/{i+1} {i+2}/{i+2}/{i+2}\n")

    return target_dir