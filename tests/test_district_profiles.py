"""
Tests for Multi-Craton District Profiles (Pan-India Exploration Scaling).
"""

import pytest
from src.geospatial.district_profiles import (
    DistrictProfile,
    list_supported_districts,
    get_district_profile,
    DISTRICT_REGISTRY,
)


def test_list_supported_districts():
    """Verify that all target critical mineral cratons are registered."""
    districts = list_supported_districts()
    assert len(districts) >= 4
    district_ids = [d["id"] for d in districts]
    assert "katghora" in district_ids
    assert "marlagalla_allapatna" in district_ids
    assert "bastar_tongpal" in district_ids
    assert "bhilwara" in district_ids


def test_katghora_profile():
    """Verify Katghora benchmark district metadata."""
    profile = get_district_profile("katghora")
    assert profile.district_id == "katghora"
    assert profile.state == "Chhattisgarh"
    assert "Chhotanagpur" in profile.craton
    assert any("Li" in m for m in profile.target_minerals)
    assert profile.epsg_code == 32644  # UTM Zone 44N
    min_lon, min_lat, max_lon, max_lat = profile.bbox
    assert min_lat < max_lat
    assert min_lon < max_lon
    assert len(profile.prior_features) >= 3


def test_marlagalla_profile():
    """Verify Marlagalla-Allapatna (Dharwar Craton) profile."""
    profile = get_district_profile("marlagalla_allapatna")
    assert profile.district_id == "marlagalla_allapatna"
    assert profile.state == "Karnataka"
    assert "Dharwar" in profile.craton
    assert "Spodumene" in profile.deposit_type
    assert profile.epsg_code == 32643  # UTM Zone 43N
    assert any("Li" in m for m in profile.target_minerals)


def test_bastar_profile():
    """Verify Bastar-Tongpal (Bastar Craton) profile."""
    profile = get_district_profile("bastar_tongpal")
    assert profile.district_id == "bastar_tongpal"
    assert profile.state == "Chhattisgarh"
    assert "Cassiterite" in profile.deposit_type
    assert any("Sn" in m for m in profile.target_minerals)
    assert any("Ta" in m for m in profile.target_minerals)


def test_bhilwara_profile():
    """Verify Bhilwara (Aravalli Craton) profile."""
    profile = get_district_profile("bhilwara")
    assert profile.district_id == "bhilwara"
    assert profile.state == "Rajasthan"
    assert "Aravalli" in profile.craton
    assert any("Li" in m for m in profile.target_minerals)
    assert any("Be" in m for m in profile.target_minerals)


def test_unknown_district():
    """Verify proper exception on unregistered district when fallback is disabled."""
    with pytest.raises(KeyError) as exc_info:
        get_district_profile("unknown_district_xyz", fallback_to_default=False)
    assert "Unsupported exploration district" in str(exc_info.value)

    # With fallback enabled, it defaults to Katghora
    fallback = get_district_profile("unknown_district_xyz", fallback_to_default=True)
    assert fallback.district_id == "katghora"


def test_profile_to_dict():
    """Verify serialization to dictionary."""
    profile = get_district_profile("katghora")
    d = profile.to_dict()
    assert isinstance(d, dict)
    assert d["district_id"] == "katghora"
    assert d["name"] == profile.name
    assert "bbox" in d
    assert d["bbox"]["min_lat"] < d["bbox"]["max_lat"]
    assert "center_coords" in d
