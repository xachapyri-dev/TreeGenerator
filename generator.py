import math
import numpy as np

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))  

class TreeMeshGenerator:
    @staticmethod
    def _normalize(v: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(v))
        if norm > 1e-6:
            return v / norm
        return np.array([0.0, 1.0, 0.0], dtype=np.float32)

    @staticmethod
    def _eval_cubic_bezier(p0, p1, p2, p3, t: float) -> np.ndarray:
        u = 1.0 - t
        return (
            (u ** 3) * p0
            + 3.0 * (u ** 2) * t * p1
            + 3.0 * u * (t ** 2) * p2
            + (t ** 3) * p3
        )

    @staticmethod
    def _eval_cubic_bezier_tangent(p0, p1, p2, p3, t: float) -> np.ndarray:
        u = 1.0 - t
        deriv = (
            3.0 * (u ** 2) * (p1 - p0)
            + 6.0 * u * t * (p2 - p1)
            + 3.0 * (t ** 2) * (p3 - p2)
        )
        return TreeMeshGenerator._normalize(deriv)

    @staticmethod
    def _build_tube(
        spine_pts: list,
        radii: list,
        radial_segments: int,
        v_tile: float = 2.0,
        root_lobes: int = 0,
        lobe_phase: float = 0.0,
    ) -> np.ndarray:
        rings = len(spine_pts)
        pts = np.asarray(spine_pts, dtype=np.float32)
        rads = np.asarray(radii, dtype=np.float32)

        tangents = np.zeros_like(pts)
        tangents[0] = TreeMeshGenerator._normalize(pts[1] - pts[0])
        tangents[-1] = TreeMeshGenerator._normalize(pts[-1] - pts[-2])
        for i in range(1, rings - 1):
            tangents[i] = TreeMeshGenerator._normalize(pts[i + 1] - pts[i - 1])

        rights = np.zeros_like(pts)
        forwards = np.zeros_like(pts)

        init_ref = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        if abs(float(np.dot(tangents[0], init_ref))) > 0.9:
            init_ref = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        rights[0] = TreeMeshGenerator._normalize(np.cross(tangents[0], init_ref))
        forwards[0] = TreeMeshGenerator._normalize(np.cross(rights[0], tangents[0]))

        for i in range(1, rings):
            t_vec = tangents[i]
            r_proj = rights[i - 1] - t_vec * float(np.dot(rights[i - 1], t_vec))
            rights[i] = TreeMeshGenerator._normalize(r_proj)
            forwards[i] = TreeMeshGenerator._normalize(np.cross(rights[i], t_vec))

        seg_lens = np.linalg.norm(pts[1:] - pts[:-1], axis=1)
        cum_lens = np.concatenate(([0.0], np.cumsum(seg_lens)))
        total_len = max(float(cum_lens[-1]), 1e-4)
        v_coords = (cum_lens / total_len) * v_tile

        u_coords = np.linspace(0.0, 1.0, radial_segments + 1, dtype=np.float32)
        angles = u_coords * (2.0 * math.pi)
        cos_a = np.cos(angles)
        sin_a = np.sin(angles)

        grid = np.zeros((rings, radial_segments + 1, 11), dtype=np.float32)

        for i in range(rings):
            t_norm = i / max(1, rings - 1)
            center = pts[i]
            r_vec = rights[i]
            f_vec = forwards[i]
            base_r = float(rads[i])

            normals = cos_a[:, None] * r_vec[None, :] + sin_a[:, None] * f_vec[None, :]
            normals_len = np.linalg.norm(normals, axis=1, keepdims=True)
            normals = normals / np.maximum(normals_len, 1e-6)

            if root_lobes > 0 and t_norm < 0.16:
                flare_strength = ((0.16 - t_norm) / 0.16) ** 2
                lobe_mod = 1.0 + 0.20 * flare_strength * np.sin(angles * root_lobes + lobe_phase)
                ring_r = (base_r * lobe_mod)[:, None]
            else:
                ring_r = base_r

            positions = center[None, :] + normals * ring_r
            tan_vecs = -sin_a[:, None] * r_vec[None, :] + cos_a[:, None] * f_vec[None, :]

            grid[i, :, 0:3] = positions
            grid[i, :, 3:6] = normals
            grid[i, :, 6] = u_coords
            grid[i, :, 7] = v_coords[i]
            grid[i, :, 8:11] = tan_vecs

        v00 = grid[:-1, :-1]
        v01 = grid[1:, :-1]
        v10 = grid[:-1, 1:]
        v11 = grid[1:, 1:]

        tris = np.stack([v00, v01, v10, v10, v01, v11], axis=2)
        return tris.reshape(-1).astype(np.float32)

    @staticmethod
    def _add_leaf_card(
        leaf_list: list,
        attach_pos: np.ndarray,
        stem_dir: np.ndarray,
        crown_center: np.ndarray,
        azimuth_around_stem: float,
        pitch_angle: float,
        roll_angle: float,
        leaf_size: float,
        leaf_root: tuple,
    ):
        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        if abs(float(np.dot(stem_dir, world_up))) > 0.92:
            world_up = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        stem_right = TreeMeshGenerator._normalize(np.cross(world_up, stem_dir))
        stem_up = TreeMeshGenerator._normalize(np.cross(stem_dir, stem_right))

        radial_out = (
            math.cos(azimuth_around_stem) * stem_right
            + math.sin(azimuth_around_stem) * stem_up
        )

        outward_from_crown = TreeMeshGenerator._normalize(attach_pos - crown_center)
        forward = TreeMeshGenerator._normalize(
            stem_dir * math.cos(pitch_angle)
            + radial_out * math.sin(pitch_angle)
            + outward_from_crown * 0.22
            + np.array([0.0, -0.08, 0.0], dtype=np.float32)
        )

        right_base = TreeMeshGenerator._normalize(np.cross(world_up, forward))
        up_base = TreeMeshGenerator._normalize(np.cross(forward, right_base))

        cos_r = math.cos(roll_angle)
        sin_r = math.sin(roll_angle)
        right = TreeMeshGenerator._normalize(cos_r * right_base + sin_r * up_base)
        face_normal = TreeMeshGenerator._normalize(np.cross(forward, right))
        if face_normal[1] < 0.0:
            face_normal = -face_normal

        bent_normal = TreeMeshGenerator._normalize(face_normal * 0.45 + outward_from_crown * 0.55)

        root_u, root_v = float(leaf_root[0]), float(leaf_root[1])
        w = leaf_size
        h = leaf_size * 1.22

        x0 = -root_u * w
        x1 = (1.0 - root_u) * w
        y0 = -root_v * h
        y1 = (1.0 - root_v) * h

        droop = np.array([0.0, -0.05 * h, 0.0], dtype=np.float32)

        p00 = attach_pos + right * x0 + forward * y0
        p10 = attach_pos + right * x1 + forward * y0
        p01 = attach_pos + right * x0 + forward * y1 + droop
        p11 = attach_pos + right * x1 + forward * y1 + droop

        n_base = bent_normal
        n_tip = TreeMeshGenerator._normalize(bent_normal + np.array([0.0, -0.18, 0.0], dtype=np.float32))

        v00 = (p00, n_base, (0.0, 0.0), right)
        v10 = (p10, n_base, (1.0, 0.0), right)
        v01 = (p01, n_tip, (0.0, 1.0), right)
        v11 = (p11, n_tip, (1.0, 1.0), right)

        for v in (v00, v10, v01, v10, v11, v01):
            leaf_list.extend([
                v[0][0], v[0][1], v[0][2],
                v[1][0], v[1][1], v[1][2],
                v[2][0], v[2][1],
                v[3][0], v[3][1], v[3][2],
            ])

    @staticmethod
    def generate(
        height: float = 12.0,
        trunk_quality: int = 16,
        branch_count: int = 14,
        sub_branch_count: int = 4,
        branch_quality: int = 8,
        leaves_per_branch: int = 35,
        leaf_root: tuple = (0.5, 0.0),
        seed: int = 42,
    ):
        rng_master = np.random.default_rng(seed)
        crown_center = np.array([0.0, height * 0.62, 0.0], dtype=np.float32)

        lean_angle = float(rng_master.uniform(0.0, 2.0 * math.pi))
        sway_mag = height * float(rng_master.uniform(0.016, 0.036))
        counter_angle = lean_angle + float(rng_master.uniform(2.1, 3.6))

        trunk_top_y = height * 0.92

        trunk_p0 = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        trunk_p1 = np.array([
            math.cos(lean_angle) * sway_mag,
            trunk_top_y * 0.34,
            math.sin(lean_angle) * sway_mag,
        ], dtype=np.float32)
        trunk_p2 = np.array([
            math.cos(counter_angle) * sway_mag * 0.8,
            trunk_top_y * 0.68,
            math.sin(counter_angle) * sway_mag * 0.8,
        ], dtype=np.float32)
        trunk_p3 = np.array([
            math.cos(lean_angle) * sway_mag * 0.25,
            trunk_top_y,
            math.sin(lean_angle) * sway_mag * 0.25,
        ], dtype=np.float32)

        base_trunk_r = height * float(rng_master.uniform(0.023, 0.029))
        root_lobes = int(rng_master.integers(4, 7))
        lobe_phase = float(rng_master.uniform(0.0, 2.0 * math.pi))
        base_azimuth_offset = float(rng_master.uniform(0.0, 2.0 * math.pi))

        def sample_trunk(t_val: float):
            pos = TreeMeshGenerator._eval_cubic_bezier(trunk_p0, trunk_p1, trunk_p2, trunk_p3, t_val)
            tangent = TreeMeshGenerator._eval_cubic_bezier_tangent(trunk_p0, trunk_p1, trunk_p2, trunk_p3, t_val)
            flare = 0.30 * ((1.0 - min(t_val / 0.14, 1.0)) ** 2.2)
            taper = ((1.0 - t_val) ** 0.78) * 0.96 + 0.035
            r = base_trunk_r * (taper + flare)
            return pos, tangent, float(r)

        trunk_rings = max(12, trunk_quality + 6)
        trunk_pts = []
        trunk_radii = []
        for i in range(trunk_rings):
            t_val = i / (trunk_rings - 1)
            pt, _, r = sample_trunk(t_val)
            trunk_pts.append(pt)
            trunk_radii.append(r)

        trunk_v = TreeMeshGenerator._build_tube(
            trunk_pts,
            trunk_radii,
            radial_segments=max(3, trunk_quality),
            v_tile=max(1.5, height * 0.35),
            root_lobes=root_lobes,
            lobe_phase=lobe_phase,
        )

        branch_nodes = []
        crown_start = 0.25
        crown_end = 0.96

        for b_idx in range(branch_count):
            rng_pos = np.random.default_rng(seed + 5000 + b_idx * 7919)

            stratum = (b_idx + 0.5) / max(1, branch_count)
            jitter_h = rng_pos.uniform(-0.28, 0.28) / max(1, branch_count)
            u_height = float(np.clip(stratum + jitter_h, 0.01, 0.99))

            az_jitter = rng_pos.uniform(-0.16, 0.16)
            azimuth = base_azimuth_offset + b_idx * GOLDEN_ANGLE + az_jitter

            branch_nodes.append([u_height, azimuth, b_idx])

        for _ in range(3):
            for i in range(len(branch_nodes)):
                for j in range(i + 1, len(branch_nodes)):
                    dh = abs(branch_nodes[i][0] - branch_nodes[j][0])
                    if dh < 0.16:
                        diff = (branch_nodes[j][1] - branch_nodes[i][1] + math.pi) % (2.0 * math.pi) - math.pi
                        min_angle = 1.15 * (1.0 - dh / 0.16)
                        if abs(diff) < min_angle:
                            push = 0.5 * (min_angle - abs(diff)) * (1.0 if diff >= 0 else -1.0)
                            branch_nodes[i][1] -= push
                            branch_nodes[j][1] += push

        branch_chunks = []
        leaf_verts = []

        b_segs = max(3, branch_quality)
        b_rings = max(7, branch_quality // 2 + 4)
        base_leaf_size = max(0.28, height * 0.042)

        for u_height, azimuth, b_idx in branch_nodes:
            rng_b = np.random.default_rng(seed + 10000 + b_idx * 1009)

            t_attach = crown_start + u_height * (crown_end - crown_start)
            attach_pt, trunk_tangent, trunk_r = sample_trunk(t_attach)

            arch_profile = math.sin(math.pi * (0.18 + 0.78 * u_height) ** 0.85)
            taper_top = 1.0 - 0.38 * (u_height ** 1.6)
            b_len = height * rng_b.uniform(0.32, 0.42) * max(0.28, arch_profile * taper_top)

            b_base_r = trunk_r * rng_b.uniform(0.44, 0.58)

            elev_angle = (0.26 + 0.72 * (u_height ** 1.15)) + rng_b.uniform(-0.06, 0.06)

            horiz_dir = np.array([math.cos(azimuth), 0.0, math.sin(azimuth)], dtype=np.float32)
            side_dir = np.array([-math.sin(azimuth), 0.0, math.cos(azimuth)], dtype=np.float32)

            initial_dir = TreeMeshGenerator._normalize(
                horiz_dir * math.cos(elev_angle)
                + np.array([0.0, math.sin(elev_angle), 0.0], dtype=np.float32)
            )

            b_p0 = attach_pt

            gnarl_1 = side_dir * (b_len * rng_b.uniform(-0.10, 0.10))
            gnarl_2 = side_dir * (b_len * rng_b.uniform(-0.12, 0.12))

            gravity_droop = ((1.0 - u_height) ** 1.4) * b_len * 0.18
            upward_reach = b_len * (0.12 + 0.18 * u_height)

            b_p1 = (
                b_p0
                + initial_dir * (b_len * 0.33)
                + gnarl_1
                + np.array([0.0, -gravity_droop * 0.35, 0.0], dtype=np.float32)
            )
            b_p2 = (
                b_p0
                + initial_dir * (b_len * 0.68)
                + gnarl_2
                + np.array([0.0, -gravity_droop * 0.85, 0.0], dtype=np.float32)
            )
            b_p3 = (
                b_p0
                + initial_dir * b_len
                + np.array([0.0, upward_reach - gravity_droop * 0.45, 0.0], dtype=np.float32)
            )

            b_pts = []
            b_radii = []
            for r_i in range(b_rings):
                s = r_i / (b_rings - 1)
                pt = TreeMeshGenerator._eval_cubic_bezier(b_p0, b_p1, b_p2, b_p3, s)
                collar = 1.15 if r_i <= 1 else 1.0
                rad = b_base_r * collar * ((1.0 - s) ** 0.78 + 0.05)
                b_pts.append(pt)
                b_radii.append(rad)

            branch_chunks.append(
                TreeMeshGenerator._build_tube(b_pts, b_radii, radial_segments=b_segs, v_tile=2.5)
            )

            tip_leaves = leaves_per_branch if sub_branch_count == 0 else max(5, leaves_per_branch // 3)
            for l_idx in range(tip_leaves):
                rng_l = np.random.default_rng(seed + 500000 + b_idx * 1009 + l_idx * 37)
                s_start = 0.28 if sub_branch_count == 0 else 0.55
                u_l = (l_idx + 0.5) / max(1, tip_leaves)
                s_leaf = s_start + (1.0 - s_start) * (1.0 - (1.0 - u_l) ** 1.25)
                s_leaf = float(np.clip(s_leaf + rng_l.uniform(-0.03, 0.03), 0.20, 0.99))

                l_pos = TreeMeshGenerator._eval_cubic_bezier(b_p0, b_p1, b_p2, b_p3, s_leaf)
                l_dir = TreeMeshGenerator._eval_cubic_bezier_tangent(b_p0, b_p1, b_p2, b_p3, s_leaf)

                az_leaf = l_idx * GOLDEN_ANGLE + rng_l.uniform(-0.25, 0.25)
                pitch_leaf = rng_l.uniform(0.45, 1.02)
                roll_leaf = rng_l.uniform(-0.38, 0.38)
                scale_var = base_leaf_size * rng_l.uniform(0.85, 1.18) * (1.06 - 0.22 * s_leaf)

                TreeMeshGenerator._add_leaf_card(
                    leaf_verts, l_pos, l_dir, crown_center, az_leaf, pitch_leaf, roll_leaf, scale_var, leaf_root
                )

            start_side = 1.0 if (b_idx % 2 == 0) else -1.0

            for s_idx in range(sub_branch_count):
                rng_s = np.random.default_rng(seed + 100000 + b_idx * 10007 + s_idx * 313)

                s_base = 0.24 + 0.64 * ((s_idx + 0.5) / max(1, sub_branch_count))
                s_attach = float(np.clip(s_base + rng_s.uniform(-0.04, 0.04), 0.20, 0.90))

                sub_origin = TreeMeshGenerator._eval_cubic_bezier(b_p0, b_p1, b_p2, b_p3, s_attach)
                parent_dir = TreeMeshGenerator._eval_cubic_bezier_tangent(b_p0, b_p1, b_p2, b_p3, s_attach)
                parent_r = b_base_r * ((1.0 - s_attach) ** 0.78 + 0.05)

                world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
                branch_side = np.cross(world_up, parent_dir)
                if np.linalg.norm(branch_side) < 1e-4:
                    branch_side = side_dir
                else:
                    branch_side = TreeMeshGenerator._normalize(branch_side)

                side_sign = start_side if (s_idx % 2 == 0) else -start_side
                spread_angle = rng_s.uniform(0.50, 0.82)
                up_tilt = rng_s.uniform(0.18, 0.42)

                outward_horiz = np.array([sub_origin[0], 0.0, sub_origin[2]], dtype=np.float32)
                outward_horiz = TreeMeshGenerator._normalize(outward_horiz)

                lateral_dir = TreeMeshGenerator._normalize(
                    branch_side * side_sign * math.cos(up_tilt)
                    + world_up * math.sin(up_tilt)
                    + outward_horiz * 0.25
                )

                sub_dir = TreeMeshGenerator._normalize(
                    parent_dir * math.cos(spread_angle) + lateral_dir * math.sin(spread_angle)
                )

                sub_len = b_len * rng_s.uniform(0.42, 0.62) * (1.10 - s_attach * 0.42)
                sub_base_r = parent_r * 0.62

                sub_p0 = sub_origin
                sub_p1 = sub_p0 + sub_dir * (sub_len * 0.35)
                sub_p2 = sub_p0 + sub_dir * (sub_len * 0.70) + np.array([0.0, sub_len * 0.05, 0.0], dtype=np.float32)
                sub_p3 = sub_p0 + sub_dir * sub_len + np.array([0.0, sub_len * 0.14, 0.0], dtype=np.float32)

                sub_rings = max(5, b_rings - 2)
                sub_pts = []
                sub_radii = []
                for sr_i in range(sub_rings):
                    st = sr_i / (sub_rings - 1)
                    sp = TreeMeshGenerator._eval_cubic_bezier(sub_p0, sub_p1, sub_p2, sub_p3, st)
                    srad = sub_base_r * ((1.0 - st) ** 0.80 + 0.06)
                    sub_pts.append(sp)
                    sub_radii.append(srad)

                branch_chunks.append(
                    TreeMeshGenerator._build_tube(
                        sub_pts, sub_radii, radial_segments=max(3, b_segs - 2), v_tile=1.5
                    )
                )

                for l_idx in range(leaves_per_branch):
                    rng_sl = np.random.default_rng(
                        seed + 900000 + b_idx * 10007 + s_idx * 313 + l_idx * 19
                    )
                    u_sl = (l_idx + 0.5) / max(1, leaves_per_branch)
                    st_base = 0.14 + 0.85 * (1.0 - (1.0 - u_sl) ** 1.2)
                    st_leaf = float(np.clip(st_base + rng_sl.uniform(-0.035, 0.035), 0.10, 0.99))

                    l_pos = TreeMeshGenerator._eval_cubic_bezier(sub_p0, sub_p1, sub_p2, sub_p3, st_leaf)
                    l_dir = TreeMeshGenerator._eval_cubic_bezier_tangent(sub_p0, sub_p1, sub_p2, sub_p3, st_leaf)

                    az_leaf = l_idx * GOLDEN_ANGLE + rng_sl.uniform(-0.22, 0.22)
                    pitch_leaf = rng_sl.uniform(0.46, 1.05)
                    roll_leaf = rng_sl.uniform(-0.42, 0.42)
                    scale_var = base_leaf_size * rng_sl.uniform(0.82, 1.16) * (1.08 - 0.22 * st_leaf)

                    TreeMeshGenerator._add_leaf_card(
                        leaf_verts, l_pos, l_dir, crown_center, az_leaf, pitch_leaf, roll_leaf, scale_var, leaf_root
                    )

        top_pt, top_tangent, top_r = sample_trunk(1.0)
        leader_count = 3
        for ldr_idx in range(leader_count):
            rng_ldr = np.random.default_rng(seed + 888000 + ldr_idx * 97)
            ldr_az = base_azimuth_offset + ldr_idx * (2.0 * math.pi / leader_count) + rng_ldr.uniform(-0.25, 0.25)
            ldr_elev = rng_ldr.uniform(0.78, 1.05)

            ldr_horiz = np.array([math.cos(ldr_az), 0.0, math.sin(ldr_az)], dtype=np.float32)
            ldr_dir = TreeMeshGenerator._normalize(
                ldr_horiz * math.cos(ldr_elev) + np.array([0.0, math.sin(ldr_elev), 0.0], dtype=np.float32)
            )
            ldr_len = height * rng_ldr.uniform(0.11, 0.16)

            lp0 = top_pt
            lp1 = lp0 + top_tangent * (ldr_len * 0.35)
            lp2 = lp0 + ldr_dir * (ldr_len * 0.72)
            lp3 = lp0 + ldr_dir * ldr_len

            ldr_rings = 5
            ldr_pts = [TreeMeshGenerator._eval_cubic_bezier(lp0, lp1, lp2, lp3, i / (ldr_rings - 1)) for i in range(ldr_rings)]
            ldr_rads = [top_r * 0.85 * ((1.0 - i / (ldr_rings - 1)) ** 0.8 + 0.1) for i in range(ldr_rings)]

            branch_chunks.append(
                TreeMeshGenerator._build_tube(ldr_pts, ldr_rads, radial_segments=max(3, b_segs - 2), v_tile=1.0)
            )

            apex_leaves = max(5, leaves_per_branch // 3)
            for a_idx in range(apex_leaves):
                rng_a = np.random.default_rng(seed + 777000 + ldr_idx * 311 + a_idx * 53)
                st_a = 0.20 + 0.78 * (a_idx / max(1, apex_leaves - 1))
                a_pos = TreeMeshGenerator._eval_cubic_bezier(lp0, lp1, lp2, lp3, st_a)
                a_dir = TreeMeshGenerator._eval_cubic_bezier_tangent(lp0, lp1, lp2, lp3, st_a)

                az_leaf = a_idx * GOLDEN_ANGLE + rng_a.uniform(-0.2, 0.2)
                pitch_leaf = rng_a.uniform(0.50, 1.10)
                roll_leaf = rng_a.uniform(-0.35, 0.35)
                scale_var = base_leaf_size * rng_a.uniform(0.85, 1.15)

                TreeMeshGenerator._add_leaf_card(
                    leaf_verts, a_pos, a_dir, crown_center, az_leaf, pitch_leaf, roll_leaf, scale_var, leaf_root
                )

        branch_v = (
            np.concatenate(branch_chunks).astype(np.float32)
            if branch_chunks
            else np.array([], dtype=np.float32)
        )
        leaf_v = np.array(leaf_verts, dtype=np.float32)

        return trunk_v, branch_v, leaf_v