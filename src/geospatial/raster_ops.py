"""
Geospatial Raster Operations & Coordinate Management.
"""

import os
import numpy as np
import tifffile


class GeoGrid:
    """
    Defines a regular latitude/longitude bounding box and pixel grid for district prospectivity.
    """
    def __init__(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float, nrows: int, ncols: int):
        self.min_lat = float(min_lat)
        self.max_lat = float(max_lat)
        self.min_lon = float(min_lon)
        self.max_lon = float(max_lon)
        self.nrows = int(nrows)
        self.ncols = int(ncols)

        self.lat_res = (self.max_lat - self.min_lat) / self.nrows
        self.lon_res = (self.max_lon - self.min_lon) / self.ncols

        self.lat_coords = np.linspace(self.max_lat - self.lat_res/2, self.min_lat + self.lat_res/2, self.nrows)
        self.lon_coords = np.linspace(self.min_lon + self.lon_res/2, self.max_lon - self.lon_res/2, self.ncols)

    def coord_to_pixel(self, lat: float, lon: float):
        """Converts lat/lon to (row, col) indices, clamped to bounds."""
        row = int(np.round((self.max_lat - lat) / self.lat_res))
        col = int(np.round((lon - self.min_lon) / self.lon_res))
        row = np.clip(row, 0, self.nrows - 1)
        col = np.clip(col, 0, self.ncols - 1)
        return row, col

    def pixel_to_coord(self, row: int, col: int):
        """Converts (row, col) to (lat, lon)."""
        lat = self.max_lat - (row + 0.5) * self.lat_res
        lon = self.min_lon + (col + 0.5) * self.lon_res
        return float(lat), float(lon)

    def get_mesh_coords(self):
        """Returns 2D meshes of (lat, lon) for every pixel."""
        lons, lats = np.meshgrid(self.lon_coords, self.lat_coords)
        return lats, lons


def write_world_file(filepath: str, grid: GeoGrid) -> str:
    """
    Writes an ESRI World File (.tfw) for the exported TIFF raster.
    Format (6 lines):
      Line 1: x-component of pixel width (degrees lon) = lon_res
      Line 2: y-component of pixel rotation (0.0)
      Line 3: x-component of pixel rotation (0.0)
      Line 4: y-component of pixel height (negative degrees lat) = -lat_res
      Line 5: x-coordinate of center of upper-left pixel = min_lon + lon_res/2
      Line 6: y-coordinate of center of upper-left pixel = max_lat - lat_res/2
    """
    base, _ = os.path.splitext(filepath)
    tfw_path = f"{base}.tfw"
    x_res = grid.lon_res
    y_res = -grid.lat_res
    x_origin = grid.min_lon + (grid.lon_res / 2.0)
    y_origin = grid.max_lat - (grid.lat_res / 2.0)
    with open(tfw_path, "w") as f:
        f.write(f"{x_res:.10f}\n0.0000000000\n0.0000000000\n{y_res:.10f}\n{x_origin:.10f}\n{y_origin:.10f}\n")
    return tfw_path


def export_geotiff(raster: np.ndarray, filepath: str, grid: GeoGrid, nodata: float = -9999.0) -> str:
    """
    Exports a 2D float32 array as a standard GeoTIFF with coordinate tags and ESRI .tfw world file.
    """
    out_raster = np.where(np.isnan(raster), nodata, raster).astype(np.float32)
    # Write GeoTIFF with CRS and bounds metadata
    tifffile.imwrite(
        filepath,
        out_raster,
        description=f"District Prospectivity Grid: bounds=({grid.min_lat},{grid.min_lon},{grid.max_lat},{grid.max_lon}) CRS=EPSG:4326"
    )
    # Generate accompanying ESRI world file (.tfw) for direct QGIS / ArcGIS ingestion
    write_world_file(filepath, grid)
    return filepath
