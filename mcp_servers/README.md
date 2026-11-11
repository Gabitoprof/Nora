# MCP servers

Each Nora tool (agenda, weather, PC control, files, home) is a server following the [MCP](https://modelcontextprotocol.io) standard, in its own subfolder. That way a new tool comes in as a plugin, without touching the core.

Planned for **v0.5.0**. Each server must declare what it can access; the user allows them one by one.
