"""Wrapper for OrcaSlicer CLI operations."""

import subprocess
import shutil
import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Any, List
import tempfile
import os

logger = logging.getLogger(__name__)

# Default timeout for slicer operations (120 seconds)
SLICER_TIMEOUT = 120

# Default filament cost per gram (PLA, adjust as needed)
DEFAULT_FILAMENT_COST_PER_GRAM = 0.03  # $0.03/gram = ~$30/kg


def find_orcaslicer_cli() -> Optional[str]:
    """Find OrcaSlicer CLI in PATH."""
    # Common names for OrcaSlicer CLI
    possible_names = ["orcaslicer", "OrcaSlicer", "OrcaSlicer-cli"]
    
    for name in possible_names:
        path = shutil.which(name)
        if path:
            return path
    
    return None


def run_slicer(
    file_path: str,
    output_dir: Optional[str] = None,
    profile_ini: Optional[str] = None,
    timeout: int = SLICER_TIMEOUT,
) -> Dict[str, Any]:
    """
    Run OrcaSlicer CLI to slice a .3mf file.
    
    Args:
        file_path: Path to .3mf file
        output_dir: Directory for slicer output (default: temp directory)
        profile_ini: Path to .ini profile file to load
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with slice results:
        {
            "estimated_time_minutes": float,
            "estimated_time_formatted": str,
            "filament_weight_grams": float,
            "filament_length_meters": float,
            "estimated_cost_usd": float,
            "warnings": List[str],
        }
        
    Raises:
        FileNotFoundError: If OrcaSlicer CLI not found
        subprocess.TimeoutExpired: If slicer times out
        ValueError: If slicer fails or output cannot be parsed
    """
    cli_path = find_orcaslicer_cli()
    if not cli_path:
        raise FileNotFoundError(
            "OrcaSlicer CLI not found in PATH. "
            "Please install OrcaSlicer and ensure it's in your PATH."
        )
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Set up output directory
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="orcaslicer_"))
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build command
    cmd = [
        cli_path,
        "--slice",
        "0",  # Slice plate 0
        "--export-slicedata",
        str(output_dir),
        str(file_path),
    ]
    
    if profile_ini:
        profile_path = Path(profile_ini)
        if not profile_path.exists():
            logger.warning(f"Profile file not found: {profile_path}")
        else:
            cmd.extend(["--load-settings", str(profile_path)])
    
    logger.info(f"Running slicer: {' '.join(cmd)}")
    
    try:
        # Run slicer
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # We'll handle errors manually
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            logger.error(f"Slicer failed with return code {result.returncode}: {error_msg}")
            raise ValueError(
                f"OrcaSlicer failed: {error_msg[:200]}"
            )
        
        # Parse output
        return parse_slicer_output(output_dir, result.stdout, result.stderr)
    
    except subprocess.TimeoutExpired:
        raise subprocess.TimeoutExpired(
            cmd, timeout, 
            f"Slicer operation timed out after {timeout} seconds. "
            "File may be too complex or system overloaded."
        )
    except Exception as e:
        logger.error(f"Error running slicer: {e}")
        raise


def parse_slicer_output(
    output_dir: Path,
    stdout: str,
    stderr: str,
) -> Dict[str, Any]:
    """
    Parse OrcaSlicer CLI output to extract metrics.
    
    Tries multiple strategies:
    1. Look for JSON file in output directory
    2. Parse text output with regex
    """
    warnings: List[str] = []
    
    # Strategy 1: Look for JSON file
    json_files = list(output_dir.glob("*.json"))
    if json_files:
        try:
            with open(json_files[0], "r") as f:
                data = json.load(f)
                return _extract_from_json(data, warnings)
        except Exception as e:
            logger.warning(f"Could not parse JSON output: {e}")
    
    # Strategy 2: Parse text output
    combined_output = stdout + "\n" + stderr
    
    # Extract time estimate
    time_minutes = _extract_time_from_text(combined_output)
    
    # Extract filament weight/length
    weight_grams = _extract_weight_from_text(combined_output)
    length_meters = _extract_length_from_text(combined_output)
    
    # Calculate cost
    cost_usd = weight_grams * DEFAULT_FILAMENT_COST_PER_GRAM if weight_grams else None
    
    # Format time
    time_formatted = _format_time(time_minutes) if time_minutes else None
    
    # Extract warnings
    if "warning" in combined_output.lower() or "error" in combined_output.lower():
        # Simple warning extraction - may need refinement
        warning_lines = [
            line.strip()
            for line in combined_output.split("\n")
            if "warning" in line.lower() or "error" in line.lower()
        ]
        warnings.extend(warning_lines[:5])  # Limit to 5 warnings
    
    return {
        "estimated_time_minutes": time_minutes,
        "estimated_time_formatted": time_formatted,
        "filament_weight_grams": weight_grams,
        "filament_length_meters": length_meters,
        "estimated_cost_usd": round(cost_usd, 2) if cost_usd else None,
        "warnings": warnings,
    }


def _extract_from_json(data: Dict[str, Any], warnings: List[str]) -> Dict[str, Any]:
    """Extract metrics from JSON data structure."""
    # This will need to be adapted based on actual OrcaSlicer JSON format
    time_minutes = data.get("estimated_time_minutes") or data.get("time_minutes")
    weight_grams = data.get("filament_weight_grams") or data.get("weight_grams")
    length_meters = data.get("filament_length_meters") or data.get("length_meters")
    
    cost_usd = weight_grams * DEFAULT_FILAMENT_COST_PER_GRAM if weight_grams else None
    time_formatted = _format_time(time_minutes) if time_minutes else None
    
    return {
        "estimated_time_minutes": time_minutes,
        "estimated_time_formatted": time_formatted,
        "filament_weight_grams": weight_grams,
        "filament_length_meters": length_meters,
        "estimated_cost_usd": round(cost_usd, 2) if cost_usd else None,
        "warnings": warnings,
    }


def _extract_time_from_text(text: str) -> Optional[float]:
    """Extract time estimate in minutes from text output."""
    # Patterns to match time estimates
    patterns = [
        r"estimated\s+time[:\s]+(\d+)\s*h(?:ours?)?\s*(\d+)\s*m(?:in(?:utes?)?)?",
        r"estimated\s+time[:\s]+(\d+)\s*m(?:in(?:utes?)?)",
        r"time[:\s]+(\d+)\s*h(?:ours?)?\s*(\d+)\s*m(?:in(?:utes?)?)",
        r"time[:\s]+(\d+)\s*m(?:in(?:utes?)?)",
        r"(\d+)\s*h(?:ours?)?\s*(\d+)\s*m(?:in(?:utes?)?)",
        r"(\d+)\s*m(?:in(?:utes?)?)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                hours = int(groups[0])
                minutes = int(groups[1])
                return hours * 60 + minutes
            elif len(groups) == 1:
                val = int(groups[0])
                # If pattern contains "h", assume hours, else minutes
                if "h" in match.group(0).lower():
                    return val * 60
                else:
                    return float(val)
    
    return None


def _extract_weight_from_text(text: str) -> Optional[float]:
    """Extract filament weight in grams from text output."""
    patterns = [
        r"filament\s+weight[:\s]+(\d+\.?\d*)\s*g(?:rams?)?",
        r"weight[:\s]+(\d+\.?\d*)\s*g(?:rams?)?",
        r"(\d+\.?\d*)\s*g(?:rams?)?\s+filament",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None


def _extract_length_from_text(text: str) -> Optional[float]:
    """Extract filament length in meters from text output."""
    patterns = [
        r"filament\s+length[:\s]+(\d+\.?\d*)\s*m(?:eters?)?",
        r"length[:\s]+(\d+\.?\d*)\s*m(?:eters?)?",
        r"(\d+\.?\d*)\s*m(?:eters?)?\s+filament",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None


def _format_time(minutes: Optional[float]) -> Optional[str]:
    """Format time in minutes as human-readable string."""
    if minutes is None:
        return None
    
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    elif mins > 0:
        return f"{mins}m"
    else:
        return "0m"

