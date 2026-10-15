import os
import shutil

def export_to_fbx(target_dir: str, model_name: str, wood_v, leaf_v, wood_texture_paths: dict, leaf_texture_paths: dict) -> str:
    os.makedirs(target_dir, exist_ok=True)
    fbx_file_path = os.path.join(target_dir, f"{model_name}.fbx")

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

    all_verts, all_norms, all_uvs, poly_indices, materials_per_poly = [], [], [], [], []

    w_count = len(wood_v) // 11
    for i in range(w_count):
        idx = i * 11
        all_verts.extend([wood_v[idx], wood_v[idx+1], wood_v[idx+2]])
        all_norms.extend([wood_v[idx+3], wood_v[idx+4], wood_v[idx+5]])
        all_uvs.extend([wood_v[idx+6], wood_v[idx+7]])
    for i in range(0, w_count, 3):
        poly_indices.extend([i, i + 1, - (i + 2) - 1])
        materials_per_poly.append(0)

    l_count = len(leaf_v) // 11
    base_v = w_count
    for i in range(l_count):
        idx = i * 11
        all_verts.extend([leaf_v[idx], leaf_v[idx+1], leaf_v[idx+2]])
        all_norms.extend([leaf_v[idx+3], leaf_v[idx+4], leaf_v[idx+5]])
        all_uvs.extend([leaf_v[idx+6], leaf_v[idx+7]])
    for i in range(0, l_count, 3):
        poly_indices.extend([base_v + i, base_v + i + 1, - (base_v + i + 2) - 1])
        materials_per_poly.append(1)

    verts_str = ",".join(f"{v:.4f}" for v in all_verts)
    norms_str = ",".join(f"{n:.4f}" for n in all_norms)
    uvs_str = ",".join(f"{u:.4f}" for u in all_uvs)
    indices_str = ",".join(str(p) for p in poly_indices)
    mat_indices_str = ",".join(str(m) for m in materials_per_poly)

    wood_albedo_name = wood_copied.get('albedo', '')
    leaf_albedo_name = leaf_copied.get('albedo', '')

    fbx_content = f"""; FBX 7.4.0 project file
FBXHeaderExtension: {{
    FBXHeaderVersion: 1003
    FBXVersion: 7400
}}
GlobalSettings: {{
    Version: 1000
    Properties70: {{
        P: "UpAxis", "int", "Integer", "",1
        P: "FrontAxis", "int", "Integer", "",2
        P: "CoordAxis", "int", "Integer", "",0
        P: "UnitScaleFactor", "double", "Number", "",100.0
    }}
}}
Objects: {{
    Geometry: 2000000, "Geometry::{model_name}_Geo", "Mesh" {{
        Vertices: *{len(all_verts)} {{ a: {verts_str} }}
        PolygonVertexIndex: *{len(poly_indices)} {{ a: {indices_str} }}
        LayerElementNormal: 0 {{
            MappingInformationType: "ByPolygonVertex"
            ReferenceInformationType: "Direct"
            Normals: *{len(all_norms)} {{ a: {norms_str} }}
        }}
        LayerElementUV: 0 {{
            MappingInformationType: "ByPolygonVertex"
            ReferenceInformationType: "Direct"
            UV: *{len(all_uvs)} {{ a: {uvs_str} }}
        }}
        LayerElementMaterial: 0 {{
            MappingInformationType: "ByPolygon"
            ReferenceInformationType: "IndexToDirect"
            Materials: *{len(materials_per_poly)} {{ a: {mat_indices_str} }}
        }}
    }}
    Model: 3000000, "Model::{model_name}", "Mesh" {{
        Version: 232
        Properties70: {{
            P: "InheritType", "enum", "", "",1
        }}
    }}
    Material: 4000001, "Material::Material_Wood", "" {{
        Version: 102
        ShadingModel: "phong"
        Properties70: {{
            P: "DiffuseColor", "Color", "", "A",0.8,0.8,0.8
        }}
    }}
    Material: 4000002, "Material::Material_Leaves", "" {{
        Version: 102
        ShadingModel: "phong"
        Properties70: {{
            P: "DiffuseColor", "Color", "", "A",0.85,0.85,0.85
        }}
    }}
    Texture: 5000001, "Texture::Wood_Albedo", "" {{
        Type: "TextureVideoClip"
        FileName: "{wood_albedo_name}"
        RelativeFilename: "{wood_albedo_name}"
    }}
    Texture: 5000002, "Texture::Leaf_Albedo", "" {{
        Type: "TextureVideoClip"
        FileName: "{leaf_albedo_name}"
        RelativeFilename: "{leaf_albedo_name}"
    }}
}}
Connections: {{
    C: "OO", 3000000, 0
    C: "OO", 2000000, 3000000
    C: "OO", 4000001, 3000000
    C: "OO", 4000002, 3000000
    C: "OP", 5000001, 4000001, "DiffuseColor"
    C: "OP", 5000002, 4000002, "DiffuseColor"
}}
"""
    with open(fbx_file_path, "w", encoding="utf-8") as f:
        f.write(fbx_content)

    return target_dir