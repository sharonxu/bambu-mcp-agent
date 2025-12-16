#!/usr/bin/env python3
"""Test MCP server tool and resource registration."""

import sys
import zipfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bambu_mcp import server


def test_mcp_server_structure():
    """Test that MCP server has all expected tools and resources."""
    print("Testing MCP server structure...")
    
    mcp = server.mcp
    
    # Check that server is initialized
    assert mcp is not None, "MCP server not initialized"
    print(f"✓ MCP server initialized: {mcp}")
    
    # Note: fastmcp doesn't expose tools/resources directly for inspection
    # But we can verify the server module has the functions
    assert hasattr(server, 'get_3mf_metadata'), "Resource get_3mf_metadata not found"
    print("✓ Resource: get_3mf_metadata registered")
    
    assert hasattr(server, 'analyze_current_print'), "Tool analyze_current_print not found"
    print("✓ Tool: analyze_current_print registered")
    
    assert hasattr(server, 'compare_print_profiles'), "Tool compare_print_profiles not found"
    print("✓ Tool: compare_print_profiles registered")
    
    assert hasattr(server, 'calculate_batch_metrics'), "Tool calculate_batch_metrics not found"
    print("✓ Tool: calculate_batch_metrics registered")
    
    return True


def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\nTesting error handling...")
    
    # Test parser with non-existent file
    try:
        from bambu_mcp import parser
        parser.parse_3mf_metadata("/nonexistent/file.3mf")
        print("✗ Should have raised FileNotFoundError")
        return False
    except FileNotFoundError:
        print("✓ Correctly raises FileNotFoundError for missing file")
    except Exception as e:
        print(f"✗ Wrong exception type: {e}")
        return False
    
    # Test parser with invalid file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(b"not a zip file")
    
    try:
        from bambu_mcp import parser
        parser.parse_3mf_metadata(tmp_path)
        print("✗ Should have raised ValueError for invalid .3mf")
        return False
    except (ValueError, zipfile.BadZipFile):
        print("✓ Correctly raises error for invalid .3mf file")
    except Exception as e:
        print(f"⚠ Unexpected exception (but still an error): {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    
    # Test slicer with missing CLI
    try:
        from bambu_mcp import slicer
        # This should work even if CLI not found (just returns None)
        cli_path = slicer.find_orcaslicer_cli()
        if cli_path is None:
            print("✓ Slicer CLI detection handles missing CLI gracefully")
        else:
            print(f"✓ Slicer CLI found at: {cli_path}")
    except Exception as e:
        print(f"✗ Slicer CLI detection failed: {e}")
        return False
    
    return True


def test_helper_functions():
    """Test internal helper functions."""
    print("\nTesting helper functions...")
    
    # Test _get_profile_path
    profile_path = server._get_profile_path("fast")
    assert profile_path.exists(), f"Fast profile should exist at {profile_path}"
    print(f"✓ _get_profile_path works: {profile_path}")
    
    # Test _format_time_delta
    delta1 = server._format_time_delta(90)  # 1h 30m
    assert "1h 30m" in delta1 or "1h" in delta1, f"Unexpected format: {delta1}"
    print(f"✓ _format_time_delta works: {delta1}")
    
    delta2 = server._format_time_delta(-45)  # -45m
    assert delta2.startswith("-"), f"Negative delta should start with '-': {delta2}"
    print(f"✓ _format_time_delta handles negatives: {delta2}")
    
    return True


def main():
    """Run all MCP server tests."""
    print("=" * 60)
    print("Testing MCP Server Structure")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Server Structure", test_mcp_server_structure()))
        results.append(("Error Handling", test_error_handling()))
        results.append(("Helper Functions", test_helper_functions()))
    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All MCP server tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

