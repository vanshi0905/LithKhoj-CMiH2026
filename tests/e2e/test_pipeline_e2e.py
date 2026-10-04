"""
LithKhoj End-to-End Multi-Craton Pipeline Test Suite.
Verifies full pipeline execution via both CLI subprocess invocation and Python API.
Ensures generation of all statutory deliverables (GeoTIFF, ESRI .tfw, GeoJSON, metrics, PDF dossier).
"""

import os
import sys
import json
import subprocess
import pytest
from typing import Dict, Any

# Ensure project root is available
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from demo_pipeline import run_pipeline
from src.geospatial.district_profiles import (
    DISTRICT_REGISTRY,
    get_district_profile,
    list_supported_districts,
)


@pytest.mark.e2e
class TestPipelineMultiCratonE2E:
    """End-to-end integration tests for LithKhoj mineral prospectivity pipeline."""

    def test_supported_districts_registry(self):
        """Verify registry contains all 4 benchmark cratons with valid attributes."""
        districts = list_supported_districts()
        assert len(districts) == 4, f"Expected 4 registered districts, got {len(districts)}"

        ids = [d["id"] for d in districts]
        assert "katghora" in ids
        assert "bhilwara" in ids
        assert "marlagalla_allapatna" in ids
        assert "bastar_tongpal" in ids

        for d in districts:
            assert d["name"]
            assert d["state"]
            assert d["craton"]
            assert d["occurrences"] > 0

    @pytest.mark.parametrize("district_id", ["katghora", "bhilwara"])
    def test_run_pipeline_api_execution(self, district_id: str, tmp_path):
        """Verify Python API execution produces complete, non-zero deliverables."""
        deliverables = run_pipeline(district=district_id, fast=True)

        assert isinstance(deliverables, dict)
        expected_keys = [
            "geotiff",
            "uncertainty_geotiff",
            "geojson",
            "metrics_json",
            "feature_rankings_csv",
            "pa_plot_png",
            "dossier_pdf",
        ]
        for key in expected_keys:
            assert key in deliverables, f"Missing deliverable key: {key}"
            fpath = deliverables[key]
            assert os.path.exists(fpath), f"Deliverable file does not exist: {fpath}"
            assert os.path.getsize(fpath) > 0, f"Deliverable file is empty: {fpath}"

        # Verify ESRI World File (.tfw) companion exists
        geotiff_path = deliverables["geotiff"]
        tfw_path = os.path.splitext(geotiff_path)[0] + ".tfw"
        assert os.path.exists(tfw_path), f"Missing ESRI world file: {tfw_path}"
        with open(tfw_path, "r") as tfw_f:
            lines = tfw_f.read().strip().splitlines()
            assert len(lines) == 6, f"Expected 6-line ESRI world file, got {len(lines)}"

        # Verify GeoJSON validity
        geojson_path = deliverables["geojson"]
        with open(geojson_path, "r", encoding="utf-8") as gf:
            data = json.load(gf)
            assert data.get("type") == "FeatureCollection"
            assert "features" in data
            if len(data["features"]) > 0:
                first_feat = data["features"][0]
                assert "properties" in first_feat
                props = first_feat["properties"]
                assert "mean_prospectivity" in props
                assert "target_id" in props

        # Verify UNFC G3 Dossier PDF format
        pdf_path = deliverables["dossier_pdf"]
        with open(pdf_path, "rb") as pf:
            header = pf.read(5)
            assert header == b"%PDF-", f"Invalid PDF header: {header}"

    def test_pipeline_cli_invocation_subprocess(self):
        """Verify CLI entrypoint behaves correctly under rapid evaluation mode."""
        cmd = [sys.executable, "demo_pipeline.py", "--district", "katghora", "--fast"]
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"CLI command failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert "DELIVERABLES SUCCESSFULLY GENERATED" in result.stdout
        assert "Area Under Success Rate Curve" in result.stdout
        assert "UNFC G3 Dossier PDF" in result.stdout
