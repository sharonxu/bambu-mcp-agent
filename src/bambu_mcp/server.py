"""MCP Server for Bambu/OrcaSlicer print analysis."""

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List

from fastmcp import FastMCP

from .parser import parse_3mf_metadata
from .slicer import run_slicer, find_orcaslicer_cli

# Configure logging to file (not stdout, to avoid breaking MCP communication)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
    ],
)

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Bambu MCP Agent")

# Get workspace directory
WORKSPACE_DIR = Path(__file__).parent.parent.parent / "mcp_workspace"
SLICE_OUTPUT_DIR = WORKSPACE_DIR / "slice_output"
SLICE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _clean_slice_output():
    """Clean temporary slice output directory."""
    if SLICE_OUTPUT_DIR.exists():
        for item in SLICE_OUTPUT_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def _get_profile_path(profile_name: str) -> Path:
    """Get path to profile .ini file."""
    return WORKSPACE_DIR / f"{profile_name}_profile.ini"


def _format_time_delta(minutes: float) -> str:
    """Format time difference as human-readable string."""
    if minutes < 0:
        sign = "-"
        minutes = abs(minutes)
    else:
        sign = "+"
    
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    
    if hours > 0:
        return f"{sign}{hours}h {mins}m" if mins > 0 else f"{sign}{hours}h"
    else:
        return f"{sign}{mins}m"


def _generate_recommendation(
    current: Dict[str, Any],
    fast: Dict[str, Any],
    balanced: Dict[str, Any],
    strong: Dict[str, Any],
) -> str:
    """Generate recommendation based on comparison results."""
    if not all(
        r.get("estimated_time_minutes") is not None
        for r in [current, fast, balanced, strong]
    ):
        return "Unable to generate recommendation: missing time estimates"
    
    current_time = current["estimated_time_minutes"]
    fast_time = fast["estimated_time_minutes"]
    balanced_time = balanced["estimated_time_minutes"]
    strong_time = strong["estimated_time_minutes"]
    
    # Find fastest
    fastest = min(fast_time, balanced_time, strong_time)
    fastest_name = "fast" if fastest == fast_time else ("balanced" if fastest == balanced_time else "strong")
    
    savings = current_time - fastest
    
    if savings > 30:  # More than 30 minutes saved
        return (
            f"Recommendation: Use {fastest_name.capitalize()} profile. "
            f"You'll save {_format_time_delta(savings)} per unit compared to current settings. "
            f"This is optimal for minimizing print time."
        )
    elif savings < -30:  # Current is actually faster
        return (
            f"Current settings are already well-optimized. "
            f"Fast profile saves only {_format_time_delta(savings)} per unit."
        )
    else:
        return (
            f"All profiles have similar print times. "
            f"Fast profile saves {_format_time_delta(savings)} per unit. "
            f"Consider your quality requirements when choosing."
        )


# Resource: 3mf://{file_path}/metadata
@mcp.resource("3mf://{file_path}/metadata")
def get_3mf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Read current print settings from a .3mf file.
    
    URI format: 3mf://{file_path}/metadata
    
    Returns metadata including filament type, nozzle diameter, layer height,
    infill density, wall loops, support settings, and previous slice info.
    """
    try:
        metadata = parse_3mf_metadata(file_path)
        logger.info(f"Successfully parsed metadata from {file_path}")
        return metadata
    except Exception as e:
        logger.error(f"Error reading metadata from {file_path}: {e}")
        raise


# Tool 1: Analyze Current Settings
@mcp.tool()
def analyze_current_print(file_path: str) -> Dict[str, Any]:
    """
    Runs slicer on existing file as-is to get baseline metrics.
    
    Args:
        file_path: Path to the .3mf file to analyze
        
    Returns:
        Dictionary with estimated time, filament weight/length, cost, and warnings
    """
    try:
        _clean_slice_output()
        
        result = run_slicer(
            file_path,
            output_dir=str(SLICE_OUTPUT_DIR),
        )
        
        logger.info(f"Successfully analyzed {file_path}")
        return result
    
    except FileNotFoundError as e:
        logger.error(f"File or CLI not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Error analyzing print: {e}")
        raise


# Tool 2: Compare Preset Profiles
@mcp.tool()
def compare_print_profiles(file_path: str) -> Dict[str, Any]:
    """
    Slices file with 3 hardcoded profiles (Fast/Balanced/Strong) and returns comparison.
    
    Args:
        file_path: Path to the .3mf file to compare
        
    Returns:
        Dictionary with comparison results for current, fast, balanced, and strong profiles,
        plus a recommendation
    """
    try:
        _clean_slice_output()
        
        # Run slicer for current settings
        logger.info("Slicing with current settings...")
        current = run_slicer(
            file_path,
            output_dir=str(SLICE_OUTPUT_DIR / "current"),
        )
        
        # Run slicer for each preset
        profiles = ["fast", "balanced", "strong"]
        results = {"current": current}
        
        for profile_name in profiles:
            logger.info(f"Slicing with {profile_name} profile...")
            profile_path = _get_profile_path(profile_name)
            
            if not profile_path.exists():
                logger.warning(f"Profile file not found: {profile_path}")
                results[profile_name] = {
                    "error": f"Profile file not found: {profile_path}"
                }
                continue
            
            try:
                profile_result = run_slicer(
                    file_path,
                    output_dir=str(SLICE_OUTPUT_DIR / profile_name),
                    profile_ini=str(profile_path),
                )
                results[profile_name] = profile_result
            except Exception as e:
                logger.error(f"Error slicing with {profile_name} profile: {e}")
                results[profile_name] = {
                    "error": str(e)
                }
        
        # Generate recommendation
        recommendation = _generate_recommendation(
            current,
            results.get("fast", {}),
            results.get("balanced", {}),
            results.get("strong", {}),
        )
        
        results["recommendation"] = recommendation
        
        logger.info("Successfully compared all profiles")
        return results
    
    except Exception as e:
        logger.error(f"Error comparing profiles: {e}")
        raise


# Tool 3: Estimate Batch Production
@mcp.tool()
def calculate_batch_metrics(
    file_path: str,
    quantity: int,
    profile_name: str = "current",
) -> Dict[str, Any]:
    """
    Calculates total time/cost for producing N units with a specific profile.
    
    Args:
        file_path: Path to the .3mf file
        quantity: Number of units to produce
        profile_name: Profile to use ("current", "fast", "balanced", or "strong")
        
    Returns:
        Dictionary with total time, cost, filament usage, and comparison vs current
    """
    try:
        if profile_name not in ["current", "fast", "balanced", "strong"]:
            raise ValueError(
                f"Invalid profile_name: {profile_name}. "
                "Must be one of: current, fast, balanced, strong"
            )
        
        _clean_slice_output()
        
        # Get baseline (current) metrics
        logger.info("Getting baseline metrics...")
        baseline = run_slicer(
            file_path,
            output_dir=str(SLICE_OUTPUT_DIR / "baseline"),
        )
        
        # Get profile metrics
        if profile_name == "current":
            profile_result = baseline
        else:
            logger.info(f"Getting metrics for {profile_name} profile...")
            profile_path = _get_profile_path(profile_name)
            
            if not profile_path.exists():
                raise FileNotFoundError(f"Profile file not found: {profile_path}")
            
            profile_result = run_slicer(
                file_path,
                output_dir=str(SLICE_OUTPUT_DIR / profile_name),
                profile_ini=str(profile_path),
            )
        
        # Calculate batch metrics
        time_per_unit = profile_result.get("estimated_time_minutes")
        weight_per_unit = profile_result.get("filament_weight_grams")
        cost_per_unit = profile_result.get("estimated_cost_usd")
        
        if time_per_unit is None:
            raise ValueError("Could not determine time per unit")
        
        total_time_minutes = time_per_unit * quantity
        total_time_hours = total_time_minutes / 60
        
        # Format total time
        days = int(total_time_hours // 24)
        hours = int(total_time_hours % 24)
        if days > 0:
            total_time_formatted = f"{days} day{'s' if days > 1 else ''}, {hours} hours"
        else:
            total_time_formatted = f"{total_time_hours:.1f} hours"
        
        # Format per unit time
        per_unit_hours = int(time_per_unit // 60)
        per_unit_mins = int(time_per_unit % 60)
        if per_unit_hours > 0:
            per_unit_time = f"{per_unit_hours}h {per_unit_mins}m"
        else:
            per_unit_time = f"{per_unit_mins}m"
        
        # Calculate totals
        total_filament_kg = (weight_per_unit * quantity / 1000) if weight_per_unit else None
        total_cost_usd = (cost_per_unit * quantity) if cost_per_unit else None
        
        # Compare vs current
        baseline_time = baseline.get("estimated_time_minutes")
        if baseline_time and profile_name != "current":
            time_delta = (time_per_unit - baseline_time) * quantity
            comparison = f"{_format_time_delta(time_delta / 60)} vs. current settings"
        else:
            comparison = "baseline"
        
        result = {
            "quantity": quantity,
            "profile": profile_name,
            "total_time_hours": round(total_time_hours, 1),
            "total_time_formatted": total_time_formatted,
            "total_filament_kg": round(total_filament_kg, 2) if total_filament_kg else None,
            "total_cost_usd": round(total_cost_usd, 2) if total_cost_usd else None,
            "per_unit_time": per_unit_time,
            "comparison_vs_current": comparison,
        }
        
        logger.info(f"Calculated batch metrics for {quantity} units with {profile_name} profile")
        return result
    
    except Exception as e:
        logger.error(f"Error calculating batch metrics: {e}")
        raise


# Main entry point
if __name__ == "__main__":
    # Check if OrcaSlicer is available
    if not find_orcaslicer_cli():
        logger.warning(
            "OrcaSlicer CLI not found in PATH. "
            "Some tools may not work. Please install OrcaSlicer."
        )
    
    mcp.run()

