# MCP Client vs Server in This Project

## The MCP Client is NOT in This Codebase

**Important**: This repository only contains the **MCP Server**. The **MCP Client** is external software that connects to this server.

## What's in This Codebase (The Server)

This codebase contains:
- ✅ **MCP Server** (`src/bambu_mcp/server.py`)
  - Exposes tools: `analyze_current_print`, `compare_print_profiles`, `calculate_batch_metrics`
  - Exposes resources: `3mf://{file_path}/metadata`
  - Uses FastMCP framework to implement the MCP protocol
  - Runs as a separate process

## What's NOT in This Codebase (The Client)

The **MCP Client** is external software that:
- Connects to this server
- Calls the tools and resources
- Presents the results to the user

### Common MCP Clients

1. **Claude Desktop** (most common for this project)
   - Location: Installed separately on your computer
   - Configuration: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - What it does: Launches this MCP server and lets Claude use its tools

2. **Cursor IDE** (if MCP support is added)
   - Would connect to this server similarly

3. **Other MCP-Compatible AIs**
   - Any AI that implements the MCP client protocol

## The Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MCP CLIENT                            │
│  (NOT in this codebase - external software)              │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Claude Desktop                                  │  │
│  │  - Launches MCP servers                          │  │
│  │  - Routes tool calls from Claude                 │  │
│  │  - Returns results to Claude                     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↕ MCP Protocol (JSON-RPC)
┌─────────────────────────────────────────────────────────┐
│                    MCP SERVER                            │
│  (THIS CODEBASE - src/bambu_mcp/server.py)              │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Tools:                                          │  │
│  │  - analyze_current_print()                      │  │
│  │  - compare_print_profiles()                     │  │
│  │  - calculate_batch_metrics()                    │  │
│  │                                                  │  │
│  │  Resources:                                      │  │
│  │  - 3mf://{file_path}/metadata                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────────┐
│              External Tools & Data                        │
│  - OrcaSlicer CLI                                        │
│  - .3mf files                                           │
│  - Profile .ini files                                    │
└─────────────────────────────────────────────────────────┘
```

## How They Connect

1. **You configure Claude Desktop** (the client) to use this server:
   ```json
   {
     "mcpServers": {
       "bambu-mcp": {
         "command": "python",
         "args": ["-m", "bambu_mcp"],
         "cwd": "/path/to/bambu-mcp-agent/src"
       }
     }
   }
   ```

2. **Claude Desktop launches** this server as a subprocess

3. **Claude Desktop communicates** with the server via:
   - **stdio** (standard input/output) - most common
   - **HTTP/SSE** - alternative transport

4. **When you ask Claude a question**, Claude Desktop:
   - Determines which tool to call
   - Sends MCP protocol message to this server
   - Server executes the tool
   - Server returns results
   - Claude Desktop gives results to Claude
   - Claude responds to you

## Code Flow Example

**User asks Claude**: "Analyze bracket.3mf"

**Claude Desktop (Client)**:
```python
# This code is NOT in this repo - it's in Claude Desktop
# Pseudo-code of what happens:

1. User types: "Analyze bracket.3mf"
2. Claude decides: "I should call analyze_current_print tool"
3. Claude Desktop sends MCP message:
   {
     "method": "tools/call",
     "params": {
       "name": "analyze_current_print",
       "arguments": {"file_path": "bracket.3mf"}
     }
   }
4. Waits for response from MCP server
```

**This Server (in this repo)**:
```python
# This IS in this repo - src/bambu_mcp/server.py

@mcp.tool()
def analyze_current_print(file_path: str) -> Dict[str, Any]:
    # Server receives MCP call
    # Executes the function
    result = run_slicer(file_path, ...)
    # Returns result via MCP protocol
    return result
```

**Claude Desktop (Client)**:
```python
# This code is NOT in this repo
# Pseudo-code:

5. Receives result from server
6. Gives result to Claude
7. Claude generates response: "Your bracket will take 75 minutes..."
```

## Why This Separation?

**Separation of Concerns**:
- **Client** (Claude Desktop): Handles AI, UI, user interaction
- **Server** (this code): Handles domain-specific tools (3D printing)

**Reusability**:
- One server can work with multiple clients
- One client can use multiple servers

**Security**:
- Server runs in isolated process
- Client controls what servers to launch
- No direct file system access from AI

## Summary

| Component | Location | What It Does |
|-----------|----------|--------------|
| **MCP Client** | Claude Desktop (external) | Connects to servers, routes tool calls, presents results |
| **MCP Server** | This codebase (`src/bambu_mcp/server.py`) | Exposes tools/resources, executes them, returns results |
| **MCP Protocol** | Standard (JSON-RPC) | How client and server communicate |

**The client is Claude Desktop (or another MCP-compatible AI). It's not in this codebase - it's the software that uses this server.**

