import os
import io
import json
import struct
import numpy as np
from PIL import Image


def export_to_glb(
    target_dir: str,
    model_name: str,
    wood_v: np.ndarray,
    leaf_v: np.ndarray,
    wood_texture_paths: dict,
    leaf_texture_paths: dict,
) -> str:
    os.makedirs(target_dir, exist_ok=True)
    glb_path = os.path.join(target_dir, f"{model_name}.glb")

    w_count = len(wood_v) // 11
    l_count = len(leaf_v) // 11

    w_pos, w_norm, w_uv = [], [], []
    for i in range(w_count):
        idx = i * 11
        w_pos.extend([wood_v[idx], wood_v[idx + 1], wood_v[idx + 2]])
        w_norm.extend([wood_v[idx + 3], wood_v[idx + 4], wood_v[idx + 5]])
        w_uv.extend([wood_v[idx + 6], 1.0 - wood_v[idx + 7]])

    l_pos, l_norm, l_uv = [], [], []
    for i in range(l_count):
        idx = i * 11
        l_pos.extend([leaf_v[idx], leaf_v[idx + 1], leaf_v[idx + 2]])
        l_norm.extend([leaf_v[idx + 3], leaf_v[idx + 4], leaf_v[idx + 5]])
        l_uv.extend([leaf_v[idx + 6], 1.0 - leaf_v[idx + 7]])

    bin_data = bytearray()

    def add_bin_floats(data_list):
        offset = len(bin_data)
        packed = struct.pack(f"<{len(data_list)}f", *data_list)
        bin_data.extend(packed)
        while len(bin_data) % 4 != 0:
            bin_data.append(0)
        return offset, len(packed)

    buffer_views = []
    images = []
    textures = []

    def embed_raw_image(file_path, name_hint="Tex"):
        if not file_path or not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            offset = len(bin_data)
            bin_data.extend(img_bytes)
            while len(bin_data) % 4 != 0:
                bin_data.append(0)
            mime = "image/png" if file_path.lower().endswith(".png") else "image/jpeg"
            bv_idx = len(buffer_views)
            buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(img_bytes)})
            img_idx = len(images)
            images.append({"bufferView": bv_idx, "mimeType": mime, "name": name_hint})
            tex_idx = len(textures)
            textures.append({"source": img_idx, "sampler": 0})
            return tex_idx
        except Exception:
            return None

    def embed_roughness_as_gltf(file_path, name_hint="Rough"):
        if not file_path or not os.path.exists(file_path):
            return None
        try:
            img = Image.open(file_path).convert("L")
            w, h = img.size
            rough_arr = np.array(img, dtype=np.uint8)
            empty = np.zeros((h, w), dtype=np.uint8)
            combined = np.stack([empty, rough_arr, empty], axis=-1)
            out_img = Image.fromarray(combined, mode="RGB")

            buf = io.BytesIO()
            out_img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            offset = len(bin_data)
            bin_data.extend(img_bytes)
            while len(bin_data) % 4 != 0:
                bin_data.append(0)

            bv_idx = len(buffer_views)
            buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(img_bytes)})
            img_idx = len(images)
            images.append({"bufferView": bv_idx, "mimeType": "image/png", "name": name_hint})
            tex_idx = len(textures)
            textures.append({"source": img_idx, "sampler": 0})
            return tex_idx
        except Exception:
            return None

    w_albedo_idx = embed_raw_image(wood_texture_paths.get("albedo"), "Wood_Albedo")
    w_normal_idx = embed_raw_image(wood_texture_paths.get("normal"), "Wood_Normal")
    w_rough_idx = embed_roughness_as_gltf(wood_texture_paths.get("rough"), "Wood_Roughness")
    w_ao_idx = embed_raw_image(wood_texture_paths.get("ao"), "Wood_AO")

    l_albedo_idx = embed_raw_image(leaf_texture_paths.get("albedo"), "Leaf_Albedo")
    l_normal_idx = embed_raw_image(leaf_texture_paths.get("normal"), "Leaf_Normal")
    l_rough_idx = embed_roughness_as_gltf(leaf_texture_paths.get("rough"), "Leaf_Roughness")
    l_ao_idx = embed_raw_image(leaf_texture_paths.get("ao"), "Leaf_AO")

    accessors = []
    primitives = []

    if w_count > 0:
        w_pos_np = np.array(w_pos, dtype=np.float32).reshape(-1, 3)
        off_p, len_p = add_bin_floats(w_pos)
        buffer_views.append({"buffer": 0, "byteOffset": off_p, "byteLength": len_p, "target": 34962})
        acc_p = len(accessors)
        accessors.append({
            "bufferView": len(buffer_views) - 1,
            "byteOffset": 0,
            "componentType": 5126,
            "count": w_count,
            "type": "VEC3",
            "min": w_pos_np.min(axis=0).tolist(),
            "max": w_pos_np.max(axis=0).tolist(),
        })

        off_n, len_n = add_bin_floats(w_norm)
        buffer_views.append({"buffer": 0, "byteOffset": off_n, "byteLength": len_n, "target": 34962})
        acc_n = len(accessors)
        accessors.append({
            "bufferView": len(buffer_views) - 1,
            "byteOffset": 0,
            "componentType": 5126,
            "count": w_count,
            "type": "VEC3",
        })

        off_u, len_u = add_bin_floats(w_uv)
        buffer_views.append({"buffer": 0, "byteOffset": off_u, "byteLength": len_u, "target": 34962})
        acc_u = len(accessors)
        accessors.append({
            "bufferView": len(buffer_views) - 1,
            "byteOffset": 0,
            "componentType": 5126,
            "count": w_count,
            "type": "VEC2",
        })

        primitives.append({
            "attributes": {"POSITION": acc_p, "NORMAL": acc_n, "TEXCOORD_0": acc_u},
            "material": 0,
            "mode": 4,
        })

    if l_count > 0:
        l_pos_np = np.array(l_pos, dtype=np.float32).reshape(-1, 3)
        off_p, len_p = add_bin_floats(l_pos)
        buffer_views.append({"buffer": 0, "byteOffset": off_p, "byteLength": len_p, "target": 34962})
        acc_p = len(accessors)
        accessors.append({
            "bufferView": len(buffer_views) - 1,
            "byteOffset": 0,
            "componentType": 5126,
            "count": l_count,
            "type": "VEC3",
            "min": l_pos_np.min(axis=0).tolist(),
            "max": l_pos_np.max(axis=0).tolist(),
        })

        off_n, len_n = add_bin_floats(l_norm)
        buffer_views.append({"buffer": 0, "byteOffset": off_n, "byteLength": len_n, "target": 34962})
        acc_n = len(accessors)
        accessors.append({
            "bufferView": len(buffer_views) - 1,
            "byteOffset": 0,
            "componentType": 5126,
            "count": l_count,
            "type": "VEC3",
        })

        off_u, len_u = add_bin_floats(l_uv)
        buffer_views.append({"buffer": 0, "byteOffset": off_u, "byteLength": len_u, "target": 34962})
        acc_u = len(accessors)
        accessors.append({
            "bufferView": len(buffer_views) - 1,
            "byteOffset": 0,
            "componentType": 5126,
            "count": l_count,
            "type": "VEC2",
        })

        primitives.append({
            "attributes": {"POSITION": acc_p, "NORMAL": acc_n, "TEXCOORD_0": acc_u},
            "material": 1,
            "mode": 4,
        })

    wood_mat = {
        "name": "Material_Wood",
        "pbrMetallicRoughness": {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "roughnessFactor": 1.0 if w_rough_idx is not None else 0.85,
            "metallicFactor": 0.0,
        },
        "doubleSided": False,
    }
    if w_albedo_idx is not None:
        wood_mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": w_albedo_idx}
    if w_rough_idx is not None:
        wood_mat["pbrMetallicRoughness"]["metallicRoughnessTexture"] = {"index": w_rough_idx}
    if w_normal_idx is not None:
        wood_mat["normalTexture"] = {"index": w_normal_idx}
    if w_ao_idx is not None:
        wood_mat["occlusionTexture"] = {"index": w_ao_idx}

    leaf_mat = {
        "name": "Material_Leaves",
        "pbrMetallicRoughness": {
            "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
            "roughnessFactor": 1.0 if l_rough_idx is not None else 0.6,
            "metallicFactor": 0.0,
        },
        "doubleSided": True,
        "alphaMode": "MASK",
        "alphaCutoff": 0.5,
    }
    if l_albedo_idx is not None:
        leaf_mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": l_albedo_idx}
    if l_rough_idx is not None:
        leaf_mat["pbrMetallicRoughness"]["metallicRoughnessTexture"] = {"index": l_rough_idx}
    if l_normal_idx is not None:
        leaf_mat["normalTexture"] = {"index": l_normal_idx}
    if l_ao_idx is not None:
        leaf_mat["occlusionTexture"] = {"index": l_ao_idx}

    gltf_dict = {
        "asset": {"version": "2.0", "generator": "TreeGenerator"},
        "scenes": [{"nodes": [0]}],
        "scene": 0,
        "nodes": [{"mesh": 0, "name": model_name}],
        "meshes": [{"name": f"{model_name}_Mesh", "primitives": primitives}],
        "materials": [wood_mat, leaf_mat],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_data)}],
    }

    if textures:
        gltf_dict["samplers"] = [{
            "magFilter": 9729,
            "minFilter": 9987,
            "wrapS": 10497,
            "wrapT": 10497,
        }]
        gltf_dict["textures"] = textures
        gltf_dict["images"] = images

    json_bytes = json.dumps(gltf_dict, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
    header = struct.pack("<4sII", b"glTF", 2, total_len)
    chunk0_hdr = struct.pack("<II", len(json_bytes), 0x4E4F534A)
    chunk1_hdr = struct.pack("<II", len(bin_data), 0x004E4942)

    with open(glb_path, "wb") as f:
        f.write(header)
        f.write(chunk0_hdr)
        f.write(json_bytes)
        f.write(chunk1_hdr)
        f.write(bin_data)

    return target_dir