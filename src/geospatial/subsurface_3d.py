"""
LithKhoj: 3D Subsurface Implicit Modeling & Drill Core Intercept Inversion.
Interpolates 3D voxel grade models (Li, Li2O, REE) from borehole collars and downhole core assays.
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from scipy.interpolate import RBFInterpolator


class Subsurface3DModel:
    """
    3D Subsurface Geostatistical Inversion and Wireframe Model.
    Transforms 1D downhole drill core assays and collar coordinates into continuous 3D grade volumes.
    """

    def __init__(
        self,
        collars_path: Optional[str] = None,
        assays_path: Optional[str] = None,
        data_dir: Optional[str] = None,
        rock_density_tpm3: float = 2.65,  # Standard density for granitic pegmatite
    ):
        self.rock_density = rock_density_tpm3
        self.data_dir = data_dir or "data"
        self.collars_df = None
        self.assays_df = None
        self.merged_df = None
        self.sample_points = None  # (N, 3) -> [Easting, Northing, RL_elevation]
        self.sample_grades = {}    # element -> (N,) float32

        # Grid bounds and arrays
        self.grid_bounds = {}
        self.grid_x = None
        self.grid_y = None
        self.grid_z = None
        self.voxel_grades = {}     # element -> (nx, ny, nz)
        self._tonnage_cache = {}

        self.collars_path = collars_path
        self.assays_path = assays_path
        if collars_path and assays_path:
            self.load_data(collars_path, assays_path)

    @property
    def df_collars(self):
        return self.collars_df

    @property
    def df_assays(self):
        return self.assays_df

    @property
    def df_merged(self):
        return self.merged_df

    def load_data(self, collars_path: Optional[str] = None, assays_path: Optional[str] = None):
        """Loads and cross-references borehole collars and downhole core assays."""
        cp = collars_path or self.collars_path or os.path.join(self.data_dir, "katghora_borehole_collars.csv")
        ap = assays_path or self.assays_path or os.path.join(self.data_dir, "katghora_drill_core_assays.csv")
        if not os.path.exists(cp) or not os.path.exists(ap):
            raise FileNotFoundError(f"Missing collar or assay file: {cp}, {ap}")

        self.collars_df = pd.read_csv(cp)
        self.assays_df = pd.read_csv(ap)

        # Merge assays with collars on borehole_id
        merged = pd.merge(
            self.assays_df,
            self.collars_df,
            on="borehole_id",
            how="inner",
            suffixes=("", "_collar"),
        )

        if len(merged) == 0:
            raise ValueError("No matching borehole_id between collars and assays.")

        self.merged_df = merged

        # Calculate 3D sample point coordinates (mid-depth of interval)
        # Note: Katghora drillholes are vertical (dip 90 degrees)
        mid_depths = (merged["from_m"] + merged["to_m"]) / 2.0
        x = merged["easting_utm44n"].values.astype(np.float64)
        y = merged["northing_utm44n"].values.astype(np.float64)
        z = (merged["collar_rl_m"] - mid_depths).values.astype(np.float64)

        self.sample_points = np.column_stack([x, y, z])

        # Extract numeric grades with safe float conversion
        for col in ["li_ppm", "li2o_pct", "total_ree_ppm", "cs_ppm", "be_ppm", "rb_ppm"]:
            if col in merged.columns:
                vals = pd.to_numeric(merged[col], errors="coerce").fillna(0.0).values.astype(np.float32)
                self.sample_grades[col] = vals

        # Compute bounding envelope with a 15% buffer
        pad_xy = 100.0  # 100m lateral expansion
        pad_z = 10.0    # 10m depth expansion
        self.grid_bounds = {
            "min_x": float(x.min() - pad_xy),
            "max_x": float(x.max() + pad_xy),
            "min_y": float(y.min() - pad_xy),
            "max_y": float(y.max() + pad_xy),
            "min_z": float(z.min() - pad_z),
            "max_z": float(z.max() + pad_z),
        }

    def interpolate_voxel_grid(
        self,
        element: str = "li_ppm",
        nx: int = 40,
        ny: int = 30,
        nz: int = 25,
        method: str = "idw",
        idw_power: float = 2.0,
    ) -> Dict[str, np.ndarray]:
        """
        Interpolates 3D voxel grid for specified mineral grade.
        Supports Fast 3D Inverse Distance Weighting ('idw') or Radial Basis Function ('rbf').
        """
        if self.sample_points is None or element not in self.sample_grades:
            raise ValueError(f"No sample data loaded for grade: {element}")

        b = self.grid_bounds
        xs = np.linspace(b["min_x"], b["max_x"], nx)
        ys = np.linspace(b["min_y"], b["max_y"], ny)
        zs = np.linspace(b["min_z"], b["max_z"], nz)

        self.grid_x, self.grid_y, self.grid_z = xs, ys, zs
        gx, gy, gz = np.meshgrid(xs, ys, zs, indexing="ij")
        grid_pts = np.column_stack([gx.ravel(), gy.ravel(), gz.ravel()])

        vals = self.sample_grades[element]

        if method == "rbf":
            try:
                # Subsample if large to maintain real-time speed
                step = 1 if len(self.sample_points) < 500 else 2
                pts_sub = self.sample_points[::step]
                vals_sub = vals[::step]
                # Normalize coordinates for RBF numerical conditioning
                scale = np.std(pts_sub, axis=0) + 1e-6
                mean = np.mean(pts_sub, axis=0)
                norm_pts = (pts_sub - mean) / scale
                norm_grid = (grid_pts - mean) / scale

                rbf = RBFInterpolator(norm_pts, vals_sub, kernel="linear", smoothing=0.1)
                pred = rbf(norm_grid).reshape(nx, ny, nz)
                pred = np.clip(pred, 0.0, None)
            except Exception:
                method = "idw"  # Fallback to IDW

        if method == "idw":
            # Anisotropic 3D IDW accelerated via spatial k-d tree
            vert_exag = 2.0
            from scipy.spatial import cKDTree

            pts_scaled = self.sample_points.copy()
            pts_scaled[:, 2] *= vert_exag
            grid_scaled = grid_pts.copy()
            grid_scaled[:, 2] *= vert_exag

            tree = cKDTree(pts_scaled)
            k_neighbors = min(15, len(self.sample_points))
            dists, idxs = tree.query(grid_scaled, k=k_neighbors)

            dists = np.maximum(dists, 1.0)
            weights = 1.0 / (dists ** idw_power)
            weights_sum = np.sum(weights, axis=1, keepdims=True)
            norm_weights = weights / weights_sum

            neighbor_vals = vals[idxs]
            pred = np.sum(norm_weights * neighbor_vals, axis=1).astype(np.float32)
            pred = pred.reshape(nx, ny, nz)

        self.voxel_grades[element] = pred
        self._tonnage_cache.clear()
        dx = (self.grid_bounds["max_x"] - self.grid_bounds["min_x"]) / (len(self.grid_x) - 1)
        dy = (self.grid_bounds["max_y"] - self.grid_bounds["min_y"]) / (len(self.grid_y) - 1)
        dz = (self.grid_bounds["max_z"] - self.grid_bounds["min_z"]) / (len(self.grid_z) - 1)
        cell_vol = float(dx * dy * dz)

        return {
            "x": xs,
            "y": ys,
            "z": zs,
            "X": gx,
            "Y": gy,
            "Z": gz,
            "grid_mesh": (gx, gy, gz),
            "values": pred,
            "grid_values": pred,
            "voxel_volume_m3": cell_vol,
        }

    def compute_tonnage_and_resource(
        self,
        element: str = "li_ppm",
        cutoff: float = 300.0,
    ) -> Dict[str, Any]:
        """
        Computes 3D orebody volume, tonnage, and contained metal above economic grade cutoff.
        Cached for O(1) interactive slider evaluation in dashboards.
        """
        cache_key = (element, round(cutoff, 2), self.rock_density)
        if cache_key in self._tonnage_cache:
            return self._tonnage_cache[cache_key].copy()

        if element not in self.voxel_grades:
            self.interpolate_voxel_grid(element)

        vals = self.voxel_grades[element]
        dx = (self.grid_bounds["max_x"] - self.grid_bounds["min_x"]) / (len(self.grid_x) - 1)
        dy = (self.grid_bounds["max_y"] - self.grid_bounds["min_y"]) / (len(self.grid_y) - 1)
        dz = (self.grid_bounds["max_z"] - self.grid_bounds["min_z"]) / (len(self.grid_z) - 1)
        cell_vol = dx * dy * dz

        mask = vals >= cutoff
        ore_cells = int(np.sum(mask))
        total_volume_m3 = ore_cells * cell_vol
        total_tonnage_mt = (total_volume_m3 * self.rock_density) / 1_000_000.0

        if ore_cells > 0:
            mean_grade = float(np.mean(vals[mask]))
            peak_grade = float(np.max(vals[mask]))
            # Contained lithium metal (tonnes) = Ore Tonnes * (ppm / 1,000,000)
            contained_li_metal_t = (total_tonnage_mt * 1_000_000.0) * (mean_grade * 1e-6)
            # Li2O conversion factor: Li2O / (2 * Li) = 29.88 / 13.88 = 2.153
            contained_li2o_t = contained_li_metal_t * 2.153
            # LCE (Lithium Carbonate Equivalent) conversion factor = 5.323 * Li metal
            contained_lce_t = contained_li_metal_t * 5.323
        else:
            mean_grade, peak_grade = 0.0, 0.0
            contained_li_metal_t, contained_li2o_t, contained_lce_t = 0.0, 0.0, 0.0

        result = {
            "element": element,
            "cutoff": cutoff,
            "ore_cells_count": ore_cells,
            "volume_m3": total_volume_m3,
            "tonnage_million_tonnes": total_tonnage_mt,
            "mean_grade_ppm": mean_grade,
            "peak_grade_ppm": peak_grade,
            "contained_li_metal_tonnes": contained_li_metal_t,
            "contained_li2o_tonnes": contained_li2o_t,
            "contained_lce_tonnes": contained_lce_t,
            "rock_density_tpm3": self.rock_density,
        }
        self._tonnage_cache[cache_key] = result
        return result

    def calculate_resource_tonnage(
        self,
        cutoff_ppm: float = 300.0,
        bulk_density: Optional[float] = None,
        element: str = "li_ppm",
    ) -> Dict[str, Any]:
        """Convenience method for calculating resource tonnage with aliases."""
        if bulk_density is not None:
            self.rock_density = bulk_density
        res = self.compute_tonnage_and_resource(element=element, cutoff=cutoff_ppm)
        res["ore_tonnes"] = res["tonnage_million_tonnes"] * 1e6
        res["total_tonnes"] = res["tonnage_million_tonnes"] * 1e6
        res["ore_volume_m3"] = res["volume_m3"]
        res["cutoff_ppm"] = cutoff_ppm
        res["total_voxels"] = (
            len(self.grid_x) * len(self.grid_y) * len(self.grid_z)
            if self.grid_x is not None
            else 0
        )
        return res

    def generate_plotly_3d(
        self,
        element: str = "li_ppm",
        cutoff: float = 300.0,
        cutoff_ppm: Optional[float] = None,
        title: str = "Katghora G3 3D Subsurface Drillhole & Mineralization Model",
        show_boreholes: bool = True,
        show_isosurface: bool = True,
    ):
        """
        Builds a full interactive Plotly 3D Figure:
        1. 3D Borehole trajectories with collar markers and labels.
        2. Sample assay markers colored by Li grade.
        3. 3D Isosurface representing the mineralized pegmatite envelope.
        """
        import plotly.graph_objects as go

        effective_cutoff = cutoff_ppm if cutoff_ppm is not None else cutoff

        if element not in self.voxel_grades:
            self.interpolate_voxel_grid(element)

        fig = go.Figure()

        # 1. Add Borehole Cylinders / Traces
        if show_boreholes:
            borehole_ids = self.collars_df["borehole_id"].unique()
            for bh_id in borehole_ids:
                collar = self.collars_df[self.collars_df["borehole_id"] == bh_id].iloc[0]
                cx, cy, cz = collar["easting_utm44n"], collar["northing_utm44n"], collar["collar_rl_m"]
                depth = collar["total_depth_m"]
                bot_z = cz - depth

                # Drillhole trajectory line
                fig.add_trace(
                    go.Scatter3d(
                        x=[cx, cx],
                        y=[cy, cy],
                        z=[cz, bot_z],
                        mode="lines+markers",
                        line=dict(color="#1e293b", width=5),
                        marker=dict(size=[6, 3], color=["#0f172a", "#64748b"]),
                        name=f"Hole {bh_id}",
                        hoverinfo="text",
                        text=[f"{bh_id} Collar (RL: {cz:.1f}m)", f"{bh_id} EOH ({depth:.1f}m)"],
                        showlegend=False,
                    )
                )

            # 2. Add Downhole Assay Points
            if self.sample_points is not None and element in self.sample_grades:
                vals = self.sample_grades[element]
                hover_text = [
                    f"Assay: {v:.1f} {element}<br>RL: {self.sample_points[i, 2]:.1f}m"
                    for i, v in enumerate(vals)
                ]
                fig.add_trace(
                    go.Scatter3d(
                        x=self.sample_points[:, 0],
                        y=self.sample_points[:, 1],
                        z=self.sample_points[:, 2],
                        mode="markers",
                        marker=dict(
                            size=3.5,
                            color=vals,
                            colorscale="Plasma",
                            cmin=float(np.percentile(vals, 5)),
                            cmax=float(np.percentile(vals, 95)),
                            colorbar=dict(title=f"{element.upper()}", len=0.6, thickness=15),
                            opacity=0.85,
                        ),
                        name="Core Assays",
                        text=hover_text,
                        hoverinfo="text",
                    )
                )

        # 3. Add 3D Isosurface of High-Grade Mineralized Envelope
        if show_isosurface:
            gx, gy, gz = np.meshgrid(self.grid_x, self.grid_y, self.grid_z, indexing="ij")
            fig.add_trace(
                go.Isosurface(
                    x=gx.flatten(),
                    y=gy.flatten(),
                    z=gz.flatten(),
                    value=self.voxel_grades[element].flatten(),
                    isomin=effective_cutoff,
                    isomax=float(np.max(self.voxel_grades[element])),
                    surface=dict(count=2, fill=0.6, pattern="all"),
                    colorscale="Viridis",
                    caps=dict(x_show=False, y_show=False, z_show=False),
                    opacity=0.35,
                    name=f"Orebody (>{effective_cutoff:.0f} ppm)",
                    showscale=False,
                )
            )

        fig.update_layout(
            title=dict(text=title, font=dict(size=15, color="#0f172a")),
            scene=dict(
                xaxis_title="UTM Easting (m)",
                yaxis_title="UTM Northing (m)",
                zaxis_title="Elevation RL (m)",
                aspectmode="manual",
                aspectratio=dict(x=1.8, y=1.2, z=0.5),
                camera=dict(eye=dict(x=1.4, y=-1.5, z=0.9)),
            ),
            margin=dict(l=0, r=0, b=0, t=40),
            paper_bgcolor="#ffffff",
        )

        return fig

    def extract_cross_section(
        self,
        axis: str = "northing",
        coord: Optional[float] = None,
        coordinate_val: Optional[float] = None,
        element: str = "li_ppm",
    ) -> Dict[str, Any]:
        """
        Extracts 2D vertical cross-section slice through the 3D voxel grid.
        axis: 'northing' / 'y' (E-W slice along constant northing) or 'easting' / 'x' (N-S slice).
        """
        if element not in self.voxel_grades:
            self.interpolate_voxel_grid(element)

        coord = coordinate_val if coordinate_val is not None else coord
        axis_lower = str(axis).lower()

        if axis_lower in ["northing", "y", "n"]:
            # Slice along Easting (X) vs RL (Z)
            y_coords = self.grid_y
            target_y = coord if coord is not None else float(np.median(y_coords))
            y_idx = int(np.argmin(np.abs(y_coords - target_y)))
            slice_data = self.voxel_grades[element][:, y_idx, :].T  # Shape: (nz, nx)
            return {
                "axis": "y" if axis_lower in ["y", "n"] else "northing",
                "axis_name": "northing",
                "fixed_coord": float(y_coords[y_idx]),
                "horiz_axis": self.grid_x,
                "vert_axis": self.grid_z,
                "horiz_coords": self.grid_x,
                "vert_coords": self.grid_z,
                "slice_grid": slice_data,
                "horiz_label": "UTM Easting (m)",
                "vert_label": "Elevation RL (m)",
            }
        else:
            # Slice along Northing (Y) vs RL (Z)
            x_coords = self.grid_x
            target_x = coord if coord is not None else float(np.median(x_coords))
            x_idx = int(np.argmin(np.abs(x_coords - target_x)))
            slice_data = self.voxel_grades[element][x_idx, :, :].T  # Shape: (nz, ny)
            return {
                "axis": "x" if axis_lower in ["x", "e"] else "easting",
                "axis_name": "easting",
                "fixed_coord": float(x_coords[x_idx]),
                "horiz_axis": self.grid_y,
                "vert_axis": self.grid_z,
                "horiz_coords": self.grid_y,
                "vert_coords": self.grid_z,
                "slice_grid": slice_data,
                "horiz_label": "UTM Northing (m)",
                "vert_label": "Elevation RL (m)",
            }

