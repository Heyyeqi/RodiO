"""Deterministic file discovery for Earth raster ingestion.

FileLoader only discovers candidate files. It intentionally does not parse,
decode, resample, or validate raster contents.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List


class FileLoader:
    """Scan a data root for named Earth raster layer files."""

    def __init__(self, data_root: str | os.PathLike[str]) -> None:
        self.data_root = Path(data_root)

    def scan(self) -> Dict[str, List[Path]]:
        """Return deterministic candidate file paths grouped by layer name."""
        return {
            "dem": self._find("dem"),
            "ocean": self._find("gebco"),
            "climate": self._find("koppen"),
            "landcover": self._find("modis"),
        }

    def _find(self, keyword: str) -> List[Path]:
        """Find files whose name contains keyword, sorted by filename."""
        if not self.data_root.exists():
            return []
        matches = [
            self.data_root / name
            for name in os.listdir(self.data_root)
            if keyword in name.lower() and (self.data_root / name).is_file()
        ]
        return sorted(matches, key=lambda path: path.name.lower())
