import os
import uuid
import shutil
import numpy as np
from PIL import Image


def export_to_unity_urp(
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

    def write_texture_meta(dst_path: str, guid_str: str, is_normal: bool = False, srgb: bool = True):
        meta_content = f"""fileFormatVersion: 2
guid: {guid_str}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 13
  mipmaps:
    mipMapMode: 0
    enableMipMap: 1
    sRGBTexture: {0 if (is_normal or not srgb) else 1}
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 1
    aniso: 1
    mipBias: 0
    wrapU: 0
    wrapV: 0
    wrapW: 0
  nPOTScale: 1
  lightmap: 0
  compressionQuality: 50
  spriteMode: 0
  spriteExtrude: 1
  spriteMeshType: 1
  alignment: 0
  spritePivot: {{x: 0.5, y: 0.5}}
  spritePixelsToUnits: 100
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 1
  alphaUsage: 1
  alphaIsTransparency: {0 if (is_normal or not srgb) else 1}
  spriteTessellationDetail: -1
  textureType: {1 if is_normal else 0}
  textureShape: 1
  singleChannelComponent: 0
"""
        with open(dst_path + ".meta", "w", encoding="utf-8") as f_meta:
            f_meta.write(meta_content)

    def export_urp_textures(paths_dict, prefix):
        saved = {}
        for slot in ("albedo", "normal", "ao", "transmission"):
            src = paths_dict.get(slot)
            if src and os.path.exists(src):
                ext = os.path.splitext(src)[1]
                filename = f"{model_name}_{prefix}_{slot.capitalize()}{ext}"
                dst_path = os.path.join(target_dir, filename)
                shutil.copy2(src, dst_path)

                g = make_guid()
                is_norm = slot == "normal"
                is_srgb = slot == "albedo"
                write_texture_meta(dst_path, g, is_normal=is_norm, srgb=is_srgb)
                saved[slot] = g

        rough_src = paths_dict.get("rough")
        if rough_src and os.path.exists(rough_src):
            try:
                img = Image.open(rough_src).convert("L")
                w, h = img.size
                rough_arr = np.array(img, dtype=np.uint8)
                smooth_arr = 255 - rough_arr
                zeros = np.zeros((h, w), dtype=np.uint8)
                rgba = np.stack([zeros, zeros, zeros, smooth_arr], axis=-1)

                ms_filename = f"{model_name}_{prefix}_MetallicSmoothness.png"
                ms_path = os.path.join(target_dir, ms_filename)
                Image.fromarray(rgba, mode="RGBA").save(ms_path, format="PNG")

                g = make_guid()
                write_texture_meta(ms_path, g, is_normal=False, srgb=False)
                saved["metallic_smoothness"] = g
            except Exception as e:
                print(f"Ошибка конвертации Roughness для URP: {e}")

        return saved

    wood_tex = export_urp_textures(wood_texture_paths, "Wood")
    leaf_tex = export_urp_textures(leaf_texture_paths, "Leaf")

    trunk_mat_guid = make_guid()
    leaf_mat_guid = make_guid()
    urp_lit_shader_guid = "933532a4fcc9baf4fa0491de14d08ed7"

    def tex_ref(g):
        return f"{{fileID: 2800000, guid: {g}, type: 3}}" if g else "{fileID: 0}"

    trunk_base = tex_ref(wood_tex.get("albedo"))
    trunk_bump = tex_ref(wood_tex.get("normal"))
    trunk_ms = tex_ref(wood_tex.get("metallic_smoothness"))
    trunk_ao = tex_ref(wood_tex.get("ao"))

    trunk_keywords = []
    if wood_tex.get("normal"):
        trunk_keywords.append("  - _NORMALMAP")
    if wood_tex.get("metallic_smoothness"):
        trunk_keywords.append("  - _METALLICSPECGLOSSMAP")
    if wood_tex.get("ao"):
        trunk_keywords.append("  - _OCCLUSIONMAP")
    trunk_kw_block = "\n".join(trunk_keywords) if trunk_keywords else "  []"

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
  m_Shader: {{fileID: 4800000, guid: {urp_lit_shader_guid}, type: 3}}
  m_ValidKeywords:
{trunk_kw_block}
  m_InvalidKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 1
  m_DoubleSidedGI: 0
  m_CustomRenderQueue: 2000
  stringTagMap:
    RenderType: Opaque
  disabledShaderPasses: []
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _BaseMap:
        m_Texture: {trunk_base}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _BumpMap:
        m_Texture: {trunk_bump}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _MainTex:
        m_Texture: {trunk_base}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _MetallicGlossMap:
        m_Texture: {trunk_ms}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _OcclusionMap:
        m_Texture: {trunk_ao}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    m_Ints: []
    m_Floats:
    - _AlphaClip: 0
    - _Blend: 0
    - _BumpScale: 1
    - _Cull: 2
    - _EnvironmentReflections: 1
    - _Metallic: 0
    - _OcclusionStrength: 1
    - _ReceiveShadows: 1
    - _Smoothness: {1.0 if wood_tex.get("metallic_smoothness") else 0.2}
    - _SmoothnessTextureChannel: 0
    - _SpecularHighlights: 1
    - _Surface: 0
    - _WorkflowMode: 1
    - _ZWrite: 1
    m_Colors:
    - _BaseColor: {{r: 1, g: 1, b: 1, a: 1}}
    - _Color: {{r: 1, g: 1, b: 1, a: 1}}
    - _EmissionColor: {{r: 0, g: 0, b: 0, a: 1}}
    - _SpecColor: {{r: 0.2, g: 0.2, b: 0.2, a: 1}}
  m_BuildTextureStacks: []
"""
    with open(trunk_mat_path, "w", encoding="utf-8") as f:
        f.write(trunk_mat_content)
    with open(trunk_mat_path + ".meta", "w", encoding="utf-8") as f:
        f.write(f"fileFormatVersion: 2\nguid: {trunk_mat_guid}\nNativeFormatImporter:\n  externalObjects: {{}}\n  mainObjectFileID: 2100000\n")

    leaf_base = tex_ref(leaf_tex.get("albedo"))
    leaf_bump = tex_ref(leaf_tex.get("normal"))
    leaf_ms = tex_ref(leaf_tex.get("metallic_smoothness"))
    leaf_ao = tex_ref(leaf_tex.get("ao"))

    leaf_keywords = ["  - _ALPHATEST_ON"]
    if leaf_tex.get("normal"):
        leaf_keywords.append("  - _NORMALMAP")
    if leaf_tex.get("metallic_smoothness"):
        leaf_keywords.append("  - _METALLICSPECGLOSSMAP")
    if leaf_tex.get("ao"):
        leaf_keywords.append("  - _OCCLUSIONMAP")
    leaf_kw_block = "\n".join(leaf_keywords)

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
  m_Shader: {{fileID: 4800000, guid: {urp_lit_shader_guid}, type: 3}}
  m_ValidKeywords:
{leaf_kw_block}
  m_InvalidKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 1
  m_DoubleSidedGI: 1
  m_CustomRenderQueue: 2450
  stringTagMap:
    RenderType: TransparentCutout
  disabledShaderPasses: []
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _BaseMap:
        m_Texture: {leaf_base}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _BumpMap:
        m_Texture: {leaf_bump}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _MainTex:
        m_Texture: {leaf_base}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _MetallicGlossMap:
        m_Texture: {leaf_ms}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    - _OcclusionMap:
        m_Texture: {leaf_ao}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    m_Ints: []
    m_Floats:
    - _AlphaClip: 1
    - _Blend: 0
    - _BumpScale: 1
    - _Cull: 0
    - _Cutoff: 0.35
    - _EnvironmentReflections: 1
    - _Metallic: 0
    - _OcclusionStrength: 1
    - _ReceiveShadows: 1
    - _Smoothness: {1.0 if leaf_tex.get("metallic_smoothness") else 0.35}
    - _SmoothnessTextureChannel: 0
    - _SpecularHighlights: 1
    - _Surface: 0
    - _WorkflowMode: 1
    - _ZWrite: 1
    m_Colors:
    - _BaseColor: {{r: 1, g: 1, b: 1, a: 1}}
    - _Color: {{r: 1, g: 1, b: 1, a: 1}}
    - _EmissionColor: {{r: 0, g: 0, b: 0, a: 1}}
    - _SpecColor: {{r: 0.2, g: 0.2, b: 0.2, a: 1}}
  m_BuildTextureStacks: []
"""
    with open(leaf_mat_path, "w", encoding="utf-8") as f:
        f.write(leaf_mat_content)
    with open(leaf_mat_path + ".meta", "w", encoding="utf-8") as f:
        f.write(f"fileFormatVersion: 2\nguid: {leaf_mat_guid}\nNativeFormatImporter:\n  externalObjects: {{}}\n  mainObjectFileID: 2100000\n")

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