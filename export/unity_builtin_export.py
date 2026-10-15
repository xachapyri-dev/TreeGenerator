import os
import uuid
import shutil


def export_to_unity_builtin(
    target_dir: str,
    model_name: str,
    wood_v,
    leaf_v,
    wood_texture_paths: dict,
    leaf_texture_paths: dict,
) -> str:

    os.makedirs(target_dir, exist_ok=True)

    def make_guid() -> str:
        return uuid.uuid4().hex

    def export_textures(paths_dict, prefix):
        saved = {}
        for slot, src in paths_dict.items():
            if src and os.path.exists(src):
                ext = os.path.splitext(src)[1]
                filename = f"{model_name}_{prefix}_{slot.capitalize()}{ext}"
                dst_path = os.path.join(target_dir, filename)
                shutil.copy2(src, dst_path)

                g = make_guid()
                is_normal = 1 if slot == "normal" else 0

                meta_content = f"""fileFormatVersion: 2
guid: {g}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 13
  textureType: {1 if is_normal else 0}
  textureShape: 1
  sRGBTexture: {0 if is_normal else 1}
  alphaSource: 1
  alphaIsTransparency: 1
  wrapU: 0
  wrapV: 0
"""
                with open(dst_path + ".meta", "w", encoding="utf-8") as f_meta:
                    f_meta.write(meta_content)
                saved[slot] = g
        return saved

    wood_tex = export_textures(wood_texture_paths, "Wood")
    leaf_tex = export_textures(leaf_texture_paths, "Leaf")

    trunk_mat_guid = make_guid()
    leaf_mat_guid = make_guid()

    def tex_ref(g):
        return f"{{fileID: 2800000, guid: {g}, type: 3}}" if g else "{fileID: 0}"

    trunk_main = tex_ref(wood_tex.get("albedo"))
    trunk_bump = tex_ref(wood_tex.get("normal"))
    trunk_gloss = tex_ref(wood_tex.get("rough"))

    leaf_main = tex_ref(leaf_tex.get("albedo"))
    leaf_bump = tex_ref(leaf_tex.get("normal"))
    leaf_extra = tex_ref(leaf_tex.get("rough"))
    leaf_sub = tex_ref(leaf_tex.get("transmission"))

    trunk_mat_path = os.path.join(target_dir, "Trunk.mat")
    trunk_mat_content = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_Name: Trunk
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_ValidKeywords:
  - _NORMALMAP
  m_InvalidKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 0
  m_DoubleSidedGI: 0
  m_CustomRenderQueue: -1
  stringTagMap: {{}}
  disabledShaderPasses: []
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _BumpMap:
        m_Texture: {trunk_bump}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _DetailMask:
        m_Texture: {trunk_gloss}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _DetailTex:
        m_Texture: {trunk_gloss}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _GlossMap:
        m_Texture: {trunk_gloss}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _MainTex:
        m_Texture: {trunk_main}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    m_Ints: []
    m_Floats:
    - _BumpScale: 1
    - _GlossMapScale: 1
    - _Shininess: 1
    - _SquashAmount: 1
    m_Colors:
    - _Color: {{r: 1, g: 1, b: 1, a: 1}}
    - _SpecColor: {{r: 0.5, g: 0.5, b: 0.5, a: 1}}
  m_BuildTextureStacks: []
"""
    with open(trunk_mat_path, "w", encoding="utf-8") as f:
        f.write(trunk_mat_content)
    with open(trunk_mat_path + ".meta", "w", encoding="utf-8") as f:
        f.write(f"fileFormatVersion: 2\nguid: {trunk_mat_guid}\nDefaultImporter:\n  externalObjects: {{}}\n")

    leaf_mat_path = os.path.join(target_dir, "Leaf.mat")
    leaf_mat_content = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_Name: Leaf
  m_Shader: {{fileID: 14002, guid: 0000000000000000f000000000000000, type: 0}}
  m_ValidKeywords:
  - EFFECT_EXTRA_TEX
  m_InvalidKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 0
  m_DoubleSidedGI: 0
  m_CustomRenderQueue: -1
  stringTagMap: {{}}
  disabledShaderPasses: []
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _BumpMap:
        m_Texture: {leaf_bump}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _ExtraTex:
        m_Texture: {leaf_extra}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _MainTex:
        m_Texture: {leaf_main}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _SubsurfaceTex:
        m_Texture: {leaf_sub}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    m_Ints: []
    m_Floats:
    - _BumpScale: 1
    - _Cutoff: 0.3
    - _Glossiness: 0.5
    - _SubsurfaceIndirect: 0.25
    m_Colors:
    - _Color: {{r: 1, g: 1, b: 1, a: 1}}
    - _SubsurfaceColor: {{r: 1, g: 1, b: 1, a: 1}}
  m_BuildTextureStacks: []
"""
    with open(leaf_mat_path, "w", encoding="utf-8") as f:
        f.write(leaf_mat_content)
    with open(leaf_mat_path + ".meta", "w", encoding="utf-8") as f:
        f.write(f"fileFormatVersion: 2\nguid: {leaf_mat_guid}\nDefaultImporter:\n  externalObjects: {{}}\n")

    def write_single_obj(part_name: str, verts, mat_guid: str) -> str:
        obj_guid = make_guid()
        mtl_guid = make_guid()
        v_count = len(verts) // 11

        mtl_path = os.path.join(target_dir, f"{part_name}.mtl")
        with open(mtl_path, "w", encoding="utf-8") as mtl:
            mtl.write(f"newmtl {part_name}\nKd 1.0 1.0 1.0\n")
        with open(mtl_path + ".meta", "w", encoding="utf-8") as mtl_meta:
            mtl_meta.write(f"fileFormatVersion: 2\nguid: {mtl_guid}\nDefaultImporter:\n  externalObjects: {{}}\n")

        obj_path = os.path.join(target_dir, f"{part_name}.obj")
        with open(obj_path, "w", encoding="utf-8") as obj:
            obj.write(f"mtllib {part_name}.mtl\n")
            for i in range(v_count):
                idx = i * 11
                obj.write(f"v {verts[idx]:.4f} {verts[idx+1]:.4f} {verts[idx+2]:.4f}\n")
            for i in range(v_count):
                idx = i * 11
                obj.write(f"vt {verts[idx+6]:.4f} {verts[idx+7]:.4f}\n")
            for i in range(v_count):
                idx = i * 11
                obj.write(f"vn {verts[idx+3]:.4f} {verts[idx+4]:.4f} {verts[idx+5]:.4f}\n")

            obj.write(f"g {part_name}\nusemtl {part_name}\n")
            for i in range(1, v_count + 1, 3):
                obj.write(f"f {i}/{i}/{i} {i+1}/{i+1}/{i+1} {i+2}/{i+2}/{i+2}\n")

        obj_meta = f"""fileFormatVersion: 2
guid: {obj_guid}
ModelImporter:
  serializedVersion: 21300
  internalIDToNameTable:
  - first:
      43: 4300000
    second: {part_name}
  externalObjects:
  - first:
      type: UnityEngine:Material
      assembly: UnityEngine.CoreModule
      name: {part_name}
    second: {{fileID: 2100000, guid: {mat_guid}, type: 2}}
  materials:
    materialImportMode: 1
    materialName: 1
    materialSearch: 1
    materialLocation: 0
  meshOptimizationFlags: 0
  importBlendShapes: 0
  importVisibility: 0
  importCameras: 0
  importLights: 0
"""
        with open(obj_path + ".meta", "w", encoding="utf-8") as f_meta:
            f_meta.write(obj_meta)

        return obj_guid

    trunk_obj_guid = write_single_obj("Trunk", wood_v, trunk_mat_guid)
    leaf_obj_guid = write_single_obj("Leaf", leaf_v, leaf_mat_guid)

    prefab_path = os.path.join(target_dir, f"{model_name}.prefab")
    prefab_guid = make_guid()

    prefab_content = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &100000
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  serializedVersion: 6
  m_Component:
  - component: {{fileID: 400000}}
  m_Layer: 0
  m_Name: {model_name}
  m_TagString: Untagged
  m_Icon: {{fileID: 0}}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &400000
Transform:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100000}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_ConstrainProportionsScale: 0
  m_Children:
  - {{fileID: 400001}}
  - {{fileID: 400002}}
  m_Father: {{fileID: 0}}
  m_RootOrder: 0
  m_LocalEulerAnglesHint: {{x: 0, y: 0, z: 0}}
--- !u!1 &100001
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  serializedVersion: 6
  m_Component:
  - component: {{fileID: 400001}}
  - component: {{fileID: 3300001}}
  - component: {{fileID: 2300001}}
  m_Layer: 0
  m_Name: Trunk
  m_TagString: Untagged
  m_Icon: {{fileID: 0}}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &400001
Transform:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100001}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_ConstrainProportionsScale: 0
  m_Children: []
  m_Father: {{fileID: 400000}}
  m_RootOrder: 0
  m_LocalEulerAnglesHint: {{x: 0, y: 0, z: 0}}
--- !u!33 &3300001
MeshFilter:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100001}}
  m_Mesh: {{fileID: 4300000, guid: {trunk_obj_guid}, type: 3}}
--- !u!23 &2300001
MeshRenderer:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100001}}
  m_Enabled: 1
  m_CastShadows: 1
  m_ReceiveShadows: 1
  m_DynamicOccludee: 1
  m_StaticShadowCaster: 0
  m_MotionVectors: 1
  m_LightProbeUsage: 1
  m_ReflectionProbeUsage: 1
  m_RayTracingMode: 2
  m_RayTraceProcedural: 0
  m_RenderingLayerMask: 1
  m_RendererPriority: 0
  m_Materials:
  - {{fileID: 2100000, guid: {trunk_mat_guid}, type: 2}}
  m_StaticBatchInfo:
    firstSubMesh: 0
    subMeshCount: 0
  m_StaticBatchRoot: {{fileID: 0}}
  m_ProbeAnchor: {{fileID: 0}}
  m_LightProbeVolumeOverride: {{fileID: 0}}
  m_ScaleInLightmap: 1
  m_ReceiveGI: 1
  m_PreserveUVs: 0
  m_IgnoreNormalsForChartDetection: 0
  m_ImportantGI: 0
  m_StitchLightmapSeams: 1
  m_SelectedEditorRenderState: 3
  m_MinimumChartSize: 4
  m_AutoUVMaxDistance: 0.5
  m_AutoUVMaxAngle: 89
  m_LightmapParameters: {{fileID: 0}}
  m_SortingLayerID: 0
  m_SortingLayer: 0
  m_SortingOrder: 0
  m_AdditionalVertexStreams: {{fileID: 0}}
--- !u!1 &100002
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  serializedVersion: 6
  m_Component:
  - component: {{fileID: 400002}}
  - component: {{fileID: 3300002}}
  - component: {{fileID: 2300002}}
  m_Layer: 0
  m_Name: Leaf
  m_TagString: Untagged
  m_Icon: {{fileID: 0}}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &400002
Transform:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100002}}
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_ConstrainProportionsScale: 0
  m_Children: []
  m_Father: {{fileID: 400000}}
  m_RootOrder: 1
  m_LocalEulerAnglesHint: {{x: 0, y: 0, z: 0}}
--- !u!33 &3300002
MeshFilter:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100002}}
  m_Mesh: {{fileID: 4300000, guid: {leaf_obj_guid}, type: 3}}
--- !u!23 &2300002
MeshRenderer:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100002}}
  m_Enabled: 1
  m_CastShadows: 1
  m_ReceiveShadows: 1
  m_DynamicOccludee: 1
  m_StaticShadowCaster: 0
  m_MotionVectors: 1
  m_LightProbeUsage: 1
  m_ReflectionProbeUsage: 1
  m_RayTracingMode: 2
  m_RayTraceProcedural: 0
  m_RenderingLayerMask: 1
  m_RendererPriority: 0
  m_Materials:
  - {{fileID: 2100000, guid: {leaf_mat_guid}, type: 2}}
  m_StaticBatchInfo:
    firstSubMesh: 0
    subMeshCount: 0
  m_StaticBatchRoot: {{fileID: 0}}
  m_ProbeAnchor: {{fileID: 0}}
  m_LightProbeVolumeOverride: {{fileID: 0}}
  m_ScaleInLightmap: 1
  m_ReceiveGI: 1
  m_PreserveUVs: 0
  m_IgnoreNormalsForChartDetection: 0
  m_ImportantGI: 0
  m_StitchLightmapSeams: 1
  m_SelectedEditorRenderState: 3
  m_MinimumChartSize: 4
  m_AutoUVMaxDistance: 0.5
  m_AutoUVMaxAngle: 89
  m_LightmapParameters: {{fileID: 0}}
  m_SortingLayerID: 0
  m_SortingLayer: 0
  m_SortingOrder: 0
  m_AdditionalVertexStreams: {{fileID: 0}}
"""
    with open(prefab_path, "w", encoding="utf-8") as f_prefab:
        f_prefab.write(prefab_content)

    with open(prefab_path + ".meta", "w", encoding="utf-8") as f_pmeta:
        f_pmeta.write(f"""fileFormatVersion: 2
guid: {prefab_guid}
PrefabImporter:
  externalObjects: {{}}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
""")

    return target_dir