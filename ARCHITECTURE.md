# Architecture Plan: Bambu/OrcaSlicer MCP

## Goals
- MCP server that inspects .3mf metadata, runs OrcaSlicer headless with preset profiles, and returns structured comparisons without modifying files.
- Deterministic, time-bounded slicing (per-call timeouts); safe temp handling; clear errors for missing CLI or bad input.

## Proposed Directory Layout
```
./
├── CLAUDE.md                     # Product brief (source of truth for scope)
├── ARCHITECTURE.md               # This plan
├── profiles/                     # Preset .ini files (fast/balanced/strong)
│   ├── fast_profile.ini
│   ├── balanced_profile.ini
│   └── strong_profile.ini
├── mcp_workspace/                # Ephemeral workspace (gitignored)
│   └── slice_output/             # Per-call slicer output, cleaned after use
└── src/
    ├── server.py                 # fastmcp entrypoint: registers tools/resources
    ├── config.py                 # Paths, timeouts, environment detection
    ├── logging_config.py         # File logger (no stdout prints)
    ├── models.py                 # Typed payloads (metadata, slice metrics)
    ├── workspace.py              # Temp dir helpers, cleanup
    ├── three_mf/                 # .3mf helpers
    │   └── metadata_reader.py    # Unzip & parse Metadata/Orca_print.config
    ├── slicer/                   # OrcaSlicer integration
    │   └── cli.py                # Run CLI, dual parse JSON/text, timeouts
    └── tools/                    # MCP tool/resource implementations
        ├── metadata_resource.py  # 3mf://.../metadata resource
        ├── analyze_current.py    # analyze_current_print tool
        ├── compare_profiles.py   # compare_print_profiles tool
        └── batch_metrics.py      # calculate_batch_metrics tool
```

## Key Components
- `config.py`: centralizes timeouts (slice 120s), workspace paths, CLI executable name (`orcaslicer`), and profile file locations. Detects executable via `shutil.which`.
- `logging_config.py`: sets up file-based logging under `mcp_workspace/debug.log`; uses Python logging to avoid stdout noise that could break MCP IPC.
- `models.py`: dataclasses for `Metadata`, `SliceMetrics`, `ProfileComparison`, and error payloads; JSON-serializable for MCP responses.
- `workspace.py`: context manager to create unique slice output dirs, ensure cleanup (even on timeout/errors), and optionally retain on debug flag.
- `three_mf/metadata_reader.py`: uses `zipfile` to read `.3mf`, parses XML `Metadata/Orca_print.config` via `ElementTree`, returns nulls for missing options, tolerates missing `slice_info.config`.
- `slicer/cli.py`: wraps OrcaSlicer CLI invocations; builds command with optional `--load-settings` preset, runs with timeout, captures stdout/stderr, reads JSON if present else regex-parses text for time/weight/cost.
- MCP server (`server.py`): initializes logger, validates CLI availability at startup, registers:
  - Resource `3mf://{file_path}/metadata` → `metadata_resource.get_metadata`.
  - Tools `analyze_current_print`, `compare_print_profiles`, `calculate_batch_metrics`.
- Tools:
  - `metadata_resource`: lightweight unzip/parse; no slicing.
  - `analyze_current_print`: run slicer on provided file; returns metrics + warnings; bubbles actionable errors (missing CLI, invalid file).
  - `compare_profiles`: runs baseline + three presets from `profiles/`; computes deltas and recommendation on the server side (not by the LLM).
  - `batch_metrics`: multiplies selected profile metrics by quantity; validates profile name.

## Data & Control Flow
1. Server startup: load config, ensure `orcaslicer` executable exists, ensure profiles are present, create `mcp_workspace/`.
2. Resource call (`metadata`):
   - Validate path → read `.3mf` via `metadata_reader` → return structured fields with nulls where absent.
3. Slice calls (`analyze_current_print` / `compare_print_profiles`):
   - Acquire temp dir from `workspace`.
   - Build CLI args (add `--load-settings` when using presets).
   - Run with timeout; on success parse JSON else regex fallback.
   - Normalize to `SliceMetrics`.
   - Cleanup temp dir.
4. `compare_profiles`: run baseline once, then three preset runs; compute deltas and recommendation string server-side.
5. `calculate_batch_metrics`: multiply metrics and format human-readable durations.

## Error Handling & Messaging
- Pre-flight: clear error if CLI not found; suggest install path.
- Input validation: verify file exists and has `.3mf` extension; friendly message if corrupted zip/XML.
- Timeout: report slicer timeout with hint to try smaller model or higher layers.
- Missing printer profile: detect CLI stderr pattern; return actionable message.
- All errors serialized; never raise unhandled exceptions through MCP.

## Logging & Telemetry
- File logger only; no stdout prints.
- Include command, duration, and parsed metrics at INFO level; stderr on WARN.
- Optional verbose flag via env var to retain temp outputs for debugging.

## Testing Strategy
- Unit: metadata parsing against fixture .3mf zips with/without optional fields.
- Integration (manual/optional): requires OrcaSlicer installed; smoke test `analyze_current_print` on a small sample file.
- Contract: schema checks for tool responses to ensure MCP outputs remain stable.

## Open Questions / Decisions
- Exact JSON schema of OrcaSlicer output per version (capture a sample during implementation).
- Where to bundle preset .ini files: ship in `profiles/` vs. generate on startup (plan: ship static files; regenerate if missing).

## Next Implementation Steps
1) Scaffold `src/` modules, logging, config, workspace helpers.  
2) Implement metadata reader and resource registration.  
3) Implement slicer CLI wrapper with timeout + dual parsing.  
4) Add tools (analyze, compare, batch) and wire into `server.py`.  
5) Add preset .ini files under `profiles/` and gitignore `mcp_workspace/`.  
6) Run lint/tests; manual CLI smoke once OrcaSlicer installed.

