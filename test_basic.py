#!/usr/bin/env python3
"""Basic tests for the MCP server components."""

import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bambu_mcp import parser, slicer


def test_parser_with_mock_3mf():
    """Test parser with a mock .3mf file."""
    print("Testing .3mf parser with mock file...")
    
    # Create a temporary .3mf file
    with tempfile.NamedTemporaryFile(suffix=".3mf", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Create a mock .3mf ZIP archive
        with zipfile.ZipFile(tmp_path, "w") as zf:
            # Create Metadata/Orca_print.config
            config_xml = """<?xml version="1.0"?>
<config>
    <option key="filament_type">PLA</option>
    <option key="nozzle_diameter">0.4</option>
    <option key="layer_height">0.20</option>
    <option key="sparse_infill_density">20</option>
    <option key="wall_loops">3</option>
    <option key="support_enable">true</option>
</config>"""
            zf.writestr("Metadata/Orca_print.config", config_xml)
            
            # Create Metadata/slice_info.config
            slice_info = "estimated_time: 75 minutes"
            zf.writestr("Metadata/slice_info.config", slice_info)
        
        # Test parsing
        metadata = parser.parse_3mf_metadata(tmp_path)
        
        # Verify results
        assert metadata["filament_type"] == "PLA", f"Expected PLA, got {metadata['filament_type']}"
        assert metadata["nozzle_diameter"] == "0.4mm", f"Expected 0.4mm, got {metadata['nozzle_diameter']}"
        assert metadata["layer_height"] == "0.20mm", f"Expected 0.20mm, got {metadata['layer_height']}"
        assert metadata["infill_density"] == "20%", f"Expected 20%, got {metadata['infill_density']}"
        assert metadata["wall_loops"] == 3, f"Expected 3, got {metadata['wall_loops']}"
        assert metadata["support_enabled"] is True, f"Expected True, got {metadata['support_enabled']}"
        assert metadata["previously_sliced"] is True, f"Expected True, got {metadata['previously_sliced']}"
        
        print("✓ Parser test passed!")
        return True
    
    except Exception as e:
        print(f"✗ Parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        Path(tmp_path).unlink(missing_ok=True)


def test_slicer_cli_detection():
    """Test slicer CLI detection."""
    print("\nTesting OrcaSlicer CLI detection...")
    
    cli_path = slicer.find_orcaslicer_cli()
    
    if cli_path:
        print(f"✓ OrcaSlicer CLI found at: {cli_path}")
        return True
    else:
        print("⚠ OrcaSlicer CLI not found in PATH (this is expected if not installed)")
        print("  The slicer tools will not work until OrcaSlicer is installed")
        return True  # Not a failure, just a warning


def test_profile_files():
    """Test that profile files exist."""
    print("\nTesting profile files...")
    
    workspace_dir = Path(__file__).parent / "mcp_workspace"
    profiles = ["fast", "balanced", "strong"]
    
    all_exist = True
    for profile in profiles:
        profile_path = workspace_dir / f"{profile}_profile.ini"
        if profile_path.exists():
            print(f"✓ {profile}_profile.ini exists")
        else:
            print(f"✗ {profile}_profile.ini not found")
            all_exist = False
    
    return all_exist


def test_server_import():
    """Test that server can be imported and initialized."""
    print("\nTesting MCP server import...")
    
    try:
        from bambu_mcp import server
        print("✓ Server module imports successfully")
        print(f"✓ MCP server initialized: {server.mcp}")
        return True
    except Exception as e:
        print(f"✗ Server import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Bambu MCP Agent")
    print("=" * 60)
    
    results = []
    
    results.append(("Parser", test_parser_with_mock_3mf()))
    results.append(("Slicer CLI Detection", test_slicer_cli_detection()))
    results.append(("Profile Files", test_profile_files()))
    results.append(("Server Import", test_server_import()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

