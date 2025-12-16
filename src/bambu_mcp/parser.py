"""Parse .3mf files to extract print settings and metadata."""

import zipfile
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


def parse_3mf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract print settings from a .3mf file.
    
    Args:
        file_path: Path to the .3mf file
        
    Returns:
        Dictionary with print settings and metadata
        
    Raises:
        ValueError: If file is not a valid .3mf archive
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.suffix.lower() == ".3mf":
        raise ValueError(f"File is not a .3mf file: {file_path}")
    
    metadata = {
        "filament_type": None,
        "nozzle_diameter": None,
        "layer_height": None,
        "infill_density": None,
        "wall_loops": None,
        "support_enabled": None,
        "previously_sliced": False,
        "last_estimate": None,
    }
    
    try:
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            # Check if previously sliced
            if "Metadata/slice_info.config" in zip_ref.namelist():
                metadata["previously_sliced"] = True
                try:
                    slice_info = zip_ref.read("Metadata/slice_info.config").decode("utf-8")
                    # Try to extract time estimate if available
                    for line in slice_info.split("\n"):
                        if "estimated_time" in line.lower() or "time" in line.lower():
                            # Basic parsing - may need refinement based on actual format
                            metadata["last_estimate"] = _extract_time_estimate(line)
                except Exception as e:
                    logger.warning(f"Could not parse slice_info.config: {e}")
            
            # Parse Orca_print.config for settings
            if "Metadata/Orca_print.config" in zip_ref.namelist():
                try:
                    config_xml = zip_ref.read("Metadata/Orca_print.config").decode("utf-8")
                    root = ET.fromstring(config_xml)
                    
                    # Extract settings from <option key="..."> elements
                    for option in root.findall(".//option"):
                        key = option.get("key", "")
                        value = option.text
                        
                        if key == "filament_type":
                            metadata["filament_type"] = value
                        elif key == "nozzle_diameter":
                            metadata["nozzle_diameter"] = f"{value}mm" if value else None
                        elif key == "layer_height":
                            metadata["layer_height"] = f"{value}mm" if value else None
                        elif key == "sparse_infill_density":
                            # Convert to percentage
                            try:
                                density = float(value) if value else None
                                if density is not None:
                                    metadata["infill_density"] = f"{density}%"
                            except (ValueError, TypeError):
                                pass
                        elif key == "wall_loops":
                            try:
                                metadata["wall_loops"] = int(value) if value else None
                            except (ValueError, TypeError):
                                pass
                        elif key == "support_enable":
                            metadata["support_enabled"] = value and value.lower() in ("true", "1", "yes")
                
                except ET.ParseError as e:
                    logger.warning(f"Could not parse Orca_print.config XML: {e}")
                except Exception as e:
                    logger.warning(f"Error reading Orca_print.config: {e}")
            else:
                logger.warning("Orca_print.config not found in .3mf file")
    
    except zipfile.BadZipFile:
        raise ValueError(f"File is not a valid .3mf archive: {file_path}")
    except Exception as e:
        logger.error(f"Unexpected error parsing .3mf file: {e}")
        raise
    
    return metadata


def _extract_time_estimate(line: str) -> Optional[str]:
    """Extract time estimate from a line of text."""
    # Simple regex-like extraction - may need refinement
    import re
    # Look for patterns like "1h 15m", "75 minutes", etc.
    time_patterns = [
        r"(\d+)\s*h(?:ours?)?\s*(\d+)\s*m(?:in(?:utes?)?)?",
        r"(\d+)\s*m(?:in(?:utes?)?)?",
        r"(\d+)\s*h(?:ours?)?",
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                return f"{match.group(1)}h {match.group(2)}m"
            elif len(match.groups()) == 1:
                val = match.group(1)
                if "h" in line.lower():
                    return f"{val}h"
                else:
                    return f"{val}m"
    
    return None

