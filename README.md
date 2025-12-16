# Bambu/OrcaSlicer MCP Agent

A Model Context Protocol (MCP) server that acts as a manufacturing consultant for 3D printing. Claude can analyze `.3mf` print files, run the slicer with different preset profiles, and recommend optimal settings for speed vs. strength trade-offs.

## Features

- **Read .3mf Metadata**: Extract current print settings from any `.3mf` file
- **Analyze Current Settings**: Run slicer on existing file to get baseline metrics
- **Compare Profiles**: Test Fast/Balanced/Strong profiles and get recommendations
- **Batch Production**: Calculate total time/cost for producing multiple units

## Prerequisites

- Python 3.10+
- OrcaSlicer installed and available in PATH (CLI mode)
- Claude Desktop with MCP support

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd bambu-mcp-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Verify OrcaSlicer CLI is available:
```bash
orcaslicer --version
```

If not found, install OrcaSlicer and ensure it's in your PATH.

## Configuration

### Claude Desktop MCP Setup

Add this to your Claude Desktop MCP configuration file (location varies by OS):

```json
{
  "mcpServers": {
    "bambu-mcp": {
      "command": "python",
      "args": ["/path/to/bambu-mcp-agent/src/bambu_mcp/server.py"]
    }
  }
}
```

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

## Usage

### Example Conversation

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

## MCP Tools

### Resource: `3mf://{file_path}/metadata`

Reads current print settings from a `.3mf` file.

**Returns:**
- Filament type
- Nozzle diameter
- Layer height
- Infill density
- Wall loops
- Support settings
- Previous slice info (if available)

### Tool: `analyze_current_print`

Runs slicer on existing file as-is to get baseline metrics.

**Arguments:**
- `file_path` (string): Path to the .3mf file

**Returns:**
- Estimated time (minutes and formatted)
- Filament weight (grams)
- Filament length (meters)
- Estimated cost (USD)
- Warnings (if any)

### Tool: `compare_print_profiles`

Slices file with 3 hardcoded profiles (Fast/Balanced/Strong) and returns comparison.

**Arguments:**
- `file_path` (string): Path to the .3mf file

**Returns:**
- Comparison results for current, fast, balanced, and strong profiles
- Recommendation based on time savings

### Tool: `calculate_batch_metrics`

Calculates total time/cost for producing N units with a specific profile.

**Arguments:**
- `file_path` (string): Path to the .3mf file
- `quantity` (integer): Number of units to produce
- `profile_name` (string): "current", "fast", "balanced", or "strong"

**Returns:**
- Total time (hours and formatted)
- Total filament (kg)
- Total cost (USD)
- Per unit time
- Comparison vs current settings

## Profile Presets

### Fast Profile
- Layer height: 0.28mm
- Infill: 10%
- Wall loops: 2
- **Use case**: Prototypes, internal parts

### Balanced Profile
- Layer height: 0.20mm
- Infill: 15%
- Wall loops: 3
- **Use case**: Most production parts

### Strong Profile
- Layer height: 0.16mm
- Infill: 25%
- Wall loops: 4
- **Use case**: Load-bearing, customer-facing

## Architecture

```
bambu-mcp-agent/
├── src/bambu_mcp/
│   ├── __init__.py
│   ├── server.py          # MCP server with tools/resources
│   ├── parser.py          # .3mf file parsing
│   └── slicer.py          # OrcaSlicer CLI wrapper
├── mcp_workspace/
│   ├── slice_output/      # Temporary slicer outputs
│   ├── fast_profile.ini
│   ├── balanced_profile.ini
│   └── strong_profile.ini
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Error Handling

The server handles common errors gracefully:

- **CLI not found**: Clear message to install OrcaSlicer
- **Invalid .3mf file**: Validation error with helpful context
- **Slicer timeout**: 120-second timeout with informative message
- **Missing printer profile**: Warning logged, operation continues if possible

## Logging

Logs are written to `debug.log` (not stdout) to avoid breaking MCP stdio communication.

## Limitations

- Does not modify `.3mf` files (read-only analysis)
- Does not handle multi-plate scenarios
- Does not validate geometric constraints
- Assumes serial printing (no multi-printer logic)

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (when implemented)
pytest
```

### Project Philosophy

**Analysis and recommendation only. No file modification.** Users manually apply settings in Bambu Studio based on recommendations.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

