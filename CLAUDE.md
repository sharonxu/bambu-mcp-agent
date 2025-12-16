# Project Mission: Bambu/OrcaSlicer MCP - Weekend Advisor

## 1. Executive Summary
Build a **Model Context Protocol (MCP) Server** that acts as a manufacturing consultant. Claude can analyze .3mf print files, run the slicer with different preset profiles, and recommend optimal settings for speed vs. strength trade-offs.

**Weekend Goal:** Claude reads a .3mf file, runs 3 comparative slices (Fast/Balanced/Strong), and presents a recommendation table with real time/cost data.

**Core Philosophy:** Analysis and recommendation only. No file modification. User manually applies settings in Bambu Studio.

## 2. Technology Stack
* **Language:** Python 3.10+
* **MCP Framework:** `fastmcp` 
* **Slicer:** OrcaSlicer CLI (headless mode)
* **File Handling:** `zipfile`, `xml.etree.ElementTree`
* **Testing:** Claude Desktop MCP integration

## 3. System Architecture

### The .3mf File Structure
```
bracket.3mf (ZIP archive)
├── Metadata/
│   ├── Orca_print.config          ← Process settings we READ
│   ├── slice_info.config          ← Pre-computed slice data
└── 3D/
    └── 3dmodel.model              ← Geometry data
```

### What This MCP Does
1. **Unzips** .3mf to read current settings
2. **Calls OrcaSlicer CLI** with override flags (no file modification)
3. **Parses output** to extract time/weight/cost
4. **Returns comparison** as structured data

### What This MCP Does NOT Do
- Modify .3mf files
- Generate new project files
- Handle multi-plate scenarios
- Validate geometric constraints

## 4. MCP Resource & Tool Definitions

### Resource: Project Metadata
```
URI: 3mf://{file_path}/metadata

Description: Read current print settings from a .3mf file

Returns:
{
  "filament_type": "PLA",
  "nozzle_diameter": "0.4mm",
  "layer_height": "0.20mm",
  "infill_density": "20%",
  "wall_loops": 3,
  "support_enabled": true,
  "previously_sliced": true,
  "last_estimate": "1h 15m" (if available)
}

Implementation notes:
- Parse Metadata/Orca_print.config XML
- Extract <option key="..."> elements
- Return null for missing values
- Do not fail if slice_info.config is absent
```

### Tool 1: Analyze Current Settings
```
Name: analyze_current_print
Arguments: file_path (string)

Description: Runs slicer on existing file as-is to get baseline metrics

CLI Command: 
  orcaslicer --slice 0 --export-slicedata {output_dir} {file_path}

Returns:
{
  "estimated_time_minutes": 75,
  "estimated_time_formatted": "1h 15m",
  "filament_weight_grams": 12.4,
  "filament_length_meters": 4.1,
  "estimated_cost_usd": 0.37,
  "warnings": [] (e.g., "Unsupported overhangs detected")
}

Error handling:
- Timeout after 120 seconds
- Return error if CLI not found
- Return error if file corrupted
```

### Tool 2: Compare Preset Profiles
```
Name: compare_print_profiles
Arguments: file_path (string)

Description: Slices file with 3 hardcoded profiles and returns comparison

Preset Profiles:
1. Fast Profile
   - layer_height: 0.28mm
   - sparse_infill_density: 10%
   - Use CLI: --load-settings fast_profile.ini

2. Balanced Profile  
   - layer_height: 0.20mm
   - sparse_infill_density: 15%
   - Use CLI: --load-settings balanced_profile.ini

3. Strong Profile
   - layer_height: 0.16mm
   - sparse_infill_density: 25%
   - Use CLI: --load-settings strong_profile.ini

Returns:
{
  "current": {...time/cost data...},
  "fast": {...time/cost data...},
  "balanced": {...time/cost data...},
  "strong": {...time/cost data...},
  "recommendation": "For 50 units, Fast saves 18 hours total"
}

Implementation notes:
- Create 3 .ini preset files during setup
- Run slicer 4 times (1 current + 3 presets)
- Parse all outputs
- Calculate deltas vs. current
- Recommendation logic in MCP server, not left to LLM
```

### Tool 3: Estimate Batch Production
```
Name: calculate_batch_metrics
Arguments: 
  - file_path (string)
  - quantity (integer)
  - profile_name (string: "current"|"fast"|"balanced"|"strong")

Description: Calculates total time/cost for producing N units

Returns:
{
  "quantity": 50,
  "profile": "fast",
  "total_time_hours": 37.5,
  "total_time_formatted": "1 day, 13.5 hours",
  "total_filament_kg": 0.62,
  "total_cost_usd": 18.60,
  "per_unit_time": "45 minutes",
  "comparison_vs_current": "-18 hours vs. current settings"
}

Notes:
- Simple multiplication, no complexity
- Assumes serial printing (no multi-printer logic)
```

## 5. Weekend Implementation Timeline

### Friday Evening (2-3 hours)
**Goal:** Validate tooling and create MCP skeleton

Tasks:
1. Install OrcaSlicer, confirm CLI works
2. Test manual slice: `orcaslicer --slice 0 --export-slicedata ./output ./test.3mf`
3. Create 3 preset .ini files (fast/balanced/strong)
4. Install `fastmcp`: `pip install fastmcp`
5. Create basic server.py with one dummy tool
6. Test MCP connection with Claude Desktop

Deliverable: Claude can call a dummy tool

### Saturday Morning (3 hours)
**Goal:** Implement metadata reading

Tasks:
1. Write function to unzip .3mf and parse XML
2. Implement `3mf://{file_path}/metadata` resource
3. Test with 3 different .3mf files from Bambu Studio
4. Handle missing fields gracefully

Deliverable: Claude can read and describe any .3mf file

### Saturday Afternoon (4 hours)
**Goal:** Implement slicer integration

Tasks:
1. Write wrapper for OrcaSlicer CLI
2. Implement `analyze_current_print` tool
3. Parse CLI output (JSON or text, depending on version)
4. Add timeout handling
5. Test with multiple file sizes (small/medium/large)

Deliverable: Claude can report actual slice estimates

### Sunday Morning (3 hours)
**Goal:** Implement profile comparison

Tasks:
1. Create 3 .ini preset files with documented settings
2. Implement `compare_print_profiles` tool
3. Run 4 slices per request (current + 3 presets)
4. Format comparison table output

Deliverable: Claude can compare all 4 options

### Sunday Afternoon (2 hours)
**Goal:** Polish and documentation

Tasks:
1. Implement `calculate_batch_metrics` tool
2. Add error messages for common failures
3. Write README.md with usage examples
4. Test end-to-end conversation flow
5. Record 2-minute demo video

Deliverable: Shippable MCP server

## 6. Profile Preset Specifications

### Fast Profile (fast_profile.ini)
```ini
# Optimized for speed, acceptable quality
layer_height = 0.28
sparse_infill_density = 10%
wall_loops = 2
top_shell_layers = 3
bottom_shell_layers = 3
infill_speed = 150
# Use case: Prototypes, internal parts
```

### Balanced Profile (balanced_profile.ini)
```ini
# Good speed/quality balance
layer_height = 0.20
sparse_infill_density = 15%
wall_loops = 3
top_shell_layers = 4
bottom_shell_layers = 4
infill_speed = 100
# Use case: Most production parts
```

### Strong Profile (strong_profile.ini)
```ini
# Maximized strength and finish
layer_height = 0.16
sparse_infill_density = 25%
wall_loops = 4
top_shell_layers = 5
bottom_shell_layers = 5
infill_speed = 80
# Use case: Load-bearing, customer-facing
```

## 7. Expected Conversation Flow

```
User: "Analyze bracket.3mf"

Claude: [calls 3mf://bracket.3mf/metadata]
        [calls analyze_current_print]
        
        Your bracket is currently set to:
        - 20% infill, 0.20mm layers
        - Estimated time: 1h 15m per part
        - Material: 12.4g PLA ($0.37)

User: "I need to print 50 for a trade show. Minimize time."

Claude: [calls compare_print_profiles]
        [calls calculate_batch_metrics with quantity=50]
        
        Here are your options:
        
        Profile    | Per Unit | 50 Units  | Savings   | Trade-off
        -----------|----------|-----------|-----------|----------
        Current    | 1h 15m   | 62.5 hrs  | baseline  | -
        Fast       | 45m      | 37.5 hrs  | -25 hrs   | Visible layers
        Balanced   | 58m      | 48.3 hrs  | -14 hrs   | Slight texture
        Strong     | 1h 32m   | 76.7 hrs  | +14 hrs   | Overkill
        
        Recommendation: Use Fast profile. You'll save a full day
        of print time. The layer lines will be visible but acceptable
        for trade show giveaways.
        
        To apply: In Bambu Studio, set layer height to 0.28mm 
        and infill to 10%.
```

## 8. Critical Implementation Notes

### CLI Output Parsing Strategy
OrcaSlicer CLI output format varies by version. Implement dual parsing:
1. **Primary:** Look for JSON file in export directory
2. **Fallback:** Parse text output with regex for "estimated time: X"

### Temporary File Management
```
./mcp_workspace/
├── slice_output/        # CLI outputs here
├── fast_profile.ini
├── balanced_profile.ini
└── strong_profile.ini
```
Clean `slice_output/` after each tool call.

### Error Messages to Handle
- "CLI not found in PATH" → Guide user to install OrcaSlicer
- "File is not a valid .3mf" → Check if file is corrupted
- "Slicer timeout" → File too complex or system overloaded
- "No printer selected" → .3mf missing printer profile

### Logging Strategy
DO NOT use `print()` (breaks MCP stdio communication).
Instead:
- Use `fastmcp` context logger
- OR write to `debug.log` file
- OR use Python `logging` module with file handler

## 9. Success Criteria

The project is complete when:

✅ Claude can analyze any .3mf file and report current settings  
✅ Claude can compare 3 preset profiles with real slice data  
✅ Claude can calculate batch production metrics  
✅ Entire conversation takes <60 seconds (4 slice operations)  
✅ Error messages are clear and actionable  
✅ Demo video posted to LinkedIn with Breaking CAD branding  

## 10. Post-Weekend Expansion Ideas

**Phase 2 (Next weekend):**
- Add custom profile generation (user specifies infill %)
- Support for multi-material prints
- Integration with filament cost databases

**Phase 3 (Future):**
- XML injection to generate modified files
- Multi-plate optimization
- Integration with Breaking CAD's design system

## 11. Breaking CAD Positioning

**Demo narrative:**
"I built an MCP that turns Claude into a manufacturing engineer. Instead of guessing print settings, Claude runs actual simulations and compares trade-offs. This is the foundation for Breaking CAD's AI-native manufacturing workflow where design, analysis, and production planning happen in natural language."

**Key talking points:**
- Bridges LLM reasoning with deterministic CAD tools
- Real data beats hallucination
- First step toward "Vibe CAD" for manufacturing