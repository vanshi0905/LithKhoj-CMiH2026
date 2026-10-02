"""
LithKhoj: Pan-India Critical Mineral District Profiles.
Provides multi-craton registry and geological parameters for automated exploration across Indian pegmatite belts.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any


@dataclass
class DistrictProfile:
    id: str
    name: str
    state: str
    craton: str
    target_minerals: List[str]
    pegmatite_type: str  # LCT (Spodumene, Lepidolite, Petalite), NYF
    bbox: Tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    utm_zone: int
    utm_hemisphere: str = "N"
    key_host_rocks: List[str] = field(default_factory=list)
    dominant_ore_minerals: List[str] = field(default_factory=list)
    geological_prior_weights: Dict[str, float] = field(default_factory=dict)
    known_occurrences_count: int = 0
    gsi_report_ref: Optional[str] = None

    @property
    def district_id(self) -> str:
        return self.id

    @property
    def epsg_code(self) -> int:
        return 32600 + self.utm_zone if self.utm_hemisphere.upper() == "N" else 32700 + self.utm_zone

    @property
    def center_coords(self) -> Tuple[float, float]:
        min_lon, min_lat, max_lon, max_lat = self.bbox
        return ((min_lat + max_lat) / 2.0, (min_lon + max_lon) / 2.0)

    @property
    def prior_features(self) -> List[str]:
        return list(self.geological_prior_weights.keys())

    @property
    def deposit_type(self) -> str:
        return self.pegmatite_type

    def to_dict(self) -> Dict[str, Any]:
        min_lon, min_lat, max_lon, max_lat = self.bbox
        return {
            "district_id": self.id,
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "craton": self.craton,
            "target_minerals": self.target_minerals,
            "pegmatite_type": self.pegmatite_type,
            "bbox": {
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
            },
            "utm_zone": self.utm_zone,
            "epsg_code": self.epsg_code,
            "center_coords": self.center_coords,
            "key_host_rocks": self.key_host_rocks,
            "dominant_ore_minerals": self.dominant_ore_minerals,
            "geological_prior_weights": self.geological_prior_weights,
            "known_occurrences_count": self.known_occurrences_count,
            "gsi_report_ref": self.gsi_report_ref,
        }


DISTRICT_REGISTRY: Dict[str, DistrictProfile] = {
    "katghora": DistrictProfile(
        id="katghora",
        name="Katghora Block, Korba District",
        state="Chhattisgarh",
        craton="Chhotanagpur Gneissic Complex (CGC) Margin",
        target_minerals=["Lithium (Li)", "Rubidium (Rb)", "Cesium (Cs)", "Beryllium (Be)", "Rare Earth Elements (REE)"],
        pegmatite_type="LCT (Lepidolite-Zinnwaldite-Spodumene)",
        bbox=(82.40, 22.40, 82.65, 22.65),  # [min_lon, min_lat, max_lon, max_lat]
        utm_zone=44,
        utm_hemisphere="N",
        key_host_rocks=["Peraluminous Leucogranite", "Biotite-Muscovite Gneiss", "Older Supracrustal Schists"],
        dominant_ore_minerals=["Lepidolite", "Spodumene", "Beryl", "Columbite-Tantalite", "Monazite"],
        geological_prior_weights={
            "crosta_pca": 0.22,
            "cardoso_lpi": 0.20,
            "cardoso_lmdr": 0.18,
            "fault_proximity": 0.15,
            "dem_slope": 0.10,
            "ngcm_geochem": 0.15,
        },
        known_occurrences_count=105,
        gsi_report_ref="GSI CRO-23909-2022 / G3 Stage Exploration",
    ),
    "marlagalla_allapatna": DistrictProfile(
        id="marlagalla_allapatna",
        name="Marlagalla-Allapatna Belt, Mandya District",
        state="Karnataka",
        craton="Western Dharwar Craton",
        target_minerals=["Lithium (Li)", "Tantalum (Ta)", "Cesium (Cs)", "Niobium (Nb)"],
        pegmatite_type="LCT (Spodumene-Dominant)",
        bbox=(76.50, 12.50, 76.90, 12.90),
        utm_zone=43,
        utm_hemisphere="N",
        key_host_rocks=["Amphibolite", "Metabasalt", "Granodioritic Gneiss"],
        dominant_ore_minerals=["Spodumene", "Columbite-Tantalite", "Cassiterite"],
        geological_prior_weights={
            "cardoso_lpi": 0.28,
            "crosta_pca": 0.20,
            "fault_proximity": 0.22,
            "dem_slope": 0.12,
            "ngcm_geochem": 0.18,
        },
        known_occurrences_count=42,
        gsi_report_ref="AMD Exploration Bulletin / Marlagalla Pegmatite Discovery",
    ),
    "bastar_tongpal": DistrictProfile(
        id="bastar_tongpal",
        name="Govindpal-Tongpal Belt, Bastar & Sukma Districts",
        state="Chhattisgarh",
        craton="Bastar Craton",
        target_minerals=["Tin (Sn)", "Tantalum (Ta)", "Niobium (Nb)", "Lithium (Li)"],
        pegmatite_type="LCT (Cassiterite-Columbite-Lepidolite)",
        bbox=(81.70, 18.60, 82.10, 19.00),
        utm_zone=44,
        utm_hemisphere="N",
        key_host_rocks=["Bengaul Supergroup Metasediments", "Paliam Granite"],
        dominant_ore_minerals=["Cassiterite", "Columbite-Tantalite", "Lepidolite", "Beryl"],
        geological_prior_weights={
            "cardoso_lmdr": 0.25,
            "crosta_pca": 0.20,
            "fault_proximity": 0.20,
            "ngcm_geochem": 0.25,
            "dem_slope": 0.10,
        },
        known_occurrences_count=35,
        gsi_report_ref="GSI Central Region Special Publication No. 26",
    ),
    "bhilwara": DistrictProfile(
        id="bhilwara",
        name="Bhilwara Mineral Belt",
        state="Rajasthan",
        craton="Aravalli Craton",
        target_minerals=["Lithium (Li)", "Beryllium (Be)", "Rare Earth Elements (REE)", "Mica"],
        pegmatite_type="LCT / NYF Mixed Pegmatite Swarms",
        bbox=(74.05, 25.05, 75.25, 25.85),
        utm_zone=43,
        utm_hemisphere="N",
        key_host_rocks=["Mangalwar Complex Gneiss", "Mica Schist"],
        dominant_ore_minerals=["Lepidolite", "Beryl", "Monazite", "Triphylite"],
        geological_prior_weights={
            "crosta_pca": 0.24,
            "cardoso_lpi": 0.18,
            "ree_neodymium": 0.20,
            "fault_proximity": 0.20,
            "dem_slope": 0.18,
        },
        known_occurrences_count=65,
        gsi_report_ref="GSI Western Region Exploration Records",
    ),
}


def get_district_profile(district_id_or_name: str, fallback_to_default: bool = False) -> DistrictProfile:
    """Retrieves district profile with tolerant fuzzy key matching."""
    key = district_id_or_name.lower().strip()
    if key in DISTRICT_REGISTRY:
        return DISTRICT_REGISTRY[key]
    for d_id, profile in DISTRICT_REGISTRY.items():
        if d_id in key or key in d_id or any(w in profile.name.lower() for w in key.split()):
            return profile
    if fallback_to_default:
        return DISTRICT_REGISTRY["katghora"]
    raise KeyError(f"Unsupported exploration district: '{district_id_or_name}'. Supported: {list(DISTRICT_REGISTRY.keys())}")


def list_supported_districts() -> List[Dict[str, str]]:
    """Returns list of supported critical mineral exploration districts."""
    return [
        {
            "id": p.id,
            "name": p.name,
            "state": p.state,
            "craton": p.craton,
            "pegmatite_type": p.pegmatite_type,
            "occurrences": p.known_occurrences_count,
        }
        for p in DISTRICT_REGISTRY.values()
    ]
