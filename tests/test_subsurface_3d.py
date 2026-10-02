"""
Tests for 3D Subsurface Geostatistical Inversion & Voxel Modeling.
"""

import os
import pytest
import numpy as np
import plotly.graph_objects as go

from src.geospatial.subsurface_3d import Subsurface3DModel

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


@pytest.fixture(scope="module")
def subsurface_model():
    """Initializes and loads the 3D Subsurface model for testing."""
    model = Subsurface3DModel(data_dir=DATA_DIR)
    model.load_data()
    return model


def test_subsurface_load_data(subsurface_model):
    """Verify loading and merging of GSI borehole collars and assays."""
    assert subsurface_model.df_collars is not None
    assert len(subsurface_model.df_collars) == 15
    assert subsurface_model.df_assays is not None
    assert len(subsurface_model.df_assays) == 453

    # Check merged assays have 3D coordinates and elements
    df_merged = subsurface_model.df_merged
    assert len(df_merged) == 453
    for col in ["easting_utm44n", "northing_utm44n", "collar_rl_m", "li_ppm"]:
        assert col in df_merged.columns
    assert (df_merged["li_ppm"].dropna() >= 0).all()
    assert (subsurface_model.sample_grades["li_ppm"] >= 0).all()
    assert (subsurface_model.sample_points[:, 2] < df_merged["collar_rl_m"]).all()


def test_voxel_grid_interpolation_idw(subsurface_model):
    """Test 3D IDW voxel interpolation on a fast grid."""
    grid_data = subsurface_model.interpolate_voxel_grid(nx=12, ny=12, nz=8, method="idw")

    assert "grid_values" in grid_data
    assert "X" in grid_data and "Y" in grid_data and "Z" in grid_data
    assert grid_data["grid_values"].shape == (12, 12, 8)
    assert grid_data["voxel_volume_m3"] > 0

    vals = grid_data["grid_values"]
    assert np.all(np.isfinite(vals))
    assert vals.min() >= 0.0
    assert vals.max() > 100.0  # Pegmatite zone captures anomalous grade


def test_resource_tonnage_calculation(subsurface_model):
    """Test UNFC resource volume and tonnage estimation under cutoffs."""
    # Fast interpolation first
    subsurface_model.interpolate_voxel_grid(nx=10, ny=10, nz=6, method="idw")

    res_300 = subsurface_model.calculate_resource_tonnage(cutoff_ppm=300.0, bulk_density=2.65)
    assert res_300["total_voxels"] == 10 * 10 * 6
    assert res_300["ore_tonnes"] >= 0
    assert res_300["contained_li_metal_tonnes"] >= 0
    assert res_300["contained_lce_tonnes"] >= 0
    assert res_300["cutoff_ppm"] == 300.0

    # Stricter cutoff should yield less or equal tonnage than lower cutoff
    res_500 = subsurface_model.calculate_resource_tonnage(cutoff_ppm=500.0, bulk_density=2.65)
    assert res_500["ore_tonnes"] <= res_300["ore_tonnes"]


def test_cross_section_extraction(subsurface_model):
    """Test vertical 2D cross-section slicing across X and Y axes."""
    subsurface_model.interpolate_voxel_grid(nx=10, ny=10, nz=6, method="idw")

    slice_y = subsurface_model.extract_cross_section(axis="y")
    assert slice_y["axis"] == "y"
    # slice_grid shape is (nz, nx) for contourf (vert x horiz)
    assert slice_y["slice_grid"].shape == (6, 10)
    assert len(slice_y["horiz_coords"]) == 10
    assert len(slice_y["vert_coords"]) == 6

    slice_x = subsurface_model.extract_cross_section(axis="x")
    assert slice_x["axis"] == "x"
    assert slice_x["slice_grid"].shape == (6, 10)


def test_generate_plotly_3d(subsurface_model):
    """Test generation of interactive 3D WebGL figure with collars and wireframe."""
    subsurface_model.interpolate_voxel_grid(nx=8, ny=8, nz=6, method="idw")
    fig = subsurface_model.generate_plotly_3d(cutoff_ppm=300.0, show_boreholes=True, show_isosurface=True)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0  # Traces exist
    # Verify 3D scene layout is set
    assert hasattr(fig.layout, "scene")
