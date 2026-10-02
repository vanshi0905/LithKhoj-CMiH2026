"""
Tests for UNFC-1997 / CRIRSCO G3 Statutory PDF Exploration Dossier Generator.
"""

import os
import tempfile
import pytest

from src.export.dossier_generator import UNFCG3DossierGenerator

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


def test_dossier_generator_init():
    """Verify initialization and folder creation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        gen = UNFCG3DossierGenerator(output_dir=tmp_dir, district_name="Test District")
        assert gen.output_dir == tmp_dir
        assert gen.district_name == "Test District"
        assert os.path.exists(tmp_dir)


def test_dossier_pdf_generation():
    """Verify generation of valid statutory multi-page PDF."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        gen = UNFCG3DossierGenerator(output_dir=tmp_dir)
        
        sample_metrics = {
            "ausrc": 0.9910,
            "optimal_threshold": 0.58,
            "exploration_density_nd": 44.67,
            "prospective_concession_pct": 2.2,
            "captured_deposits_pct": 100.0,
            "barren_ground_screened_pct": 97.8,
            "drilling_cost_savings_inr_cr": 22.5,
        }

        geojson_path = os.path.join(OUTPUT_DIR, "katghora_lithium_targets.geojson")
        target_file = "test_statutory_dossier.pdf"

        out_path = gen.generate_dossier_pdf(
            targets_geojson_path=geojson_path if os.path.exists(geojson_path) else None,
            metrics_dict=sample_metrics,
            output_filename=target_file,
        )

        assert os.path.exists(out_path)
        file_size = os.path.getsize(out_path)
        assert file_size > 5000, f"Expected PDF > 5KB, got {file_size} bytes"

        # Verify PDF header magic bytes
        with open(out_path, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-", "File must have valid PDF magic signature"
