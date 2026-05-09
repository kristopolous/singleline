#!/usr/bin/env python3
"""
singleline — Compile a tools.txt spec into MCP tool definitions.

Usage:
    singleline --mcp tools.txt --lang python > tools.py
    singleline --mcp tools.txt --lang typescript > tools.ts
"""

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass, field

from jinja2 import Environment, DictLoader


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Tool:
    name: str
    template: str          # e.g. '/usr/bin/env bash -c "{command}"'
    params: list[str]      # e.g. ['command']
    description: str = ""  # optional, from a comment line like  #! description


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def extract_fstring_params(template: str) -> list[str]:
    """Extract {placeholder} names from an f-string-like template."""
    params = []
    # Match {word} but not {{escaped}}
    for m in re.finditer(r"(?<!\{)\{(\w+)\}(?!\})", template):
        params.append(m.group(1))
    return params


def parse_line(raw: str) -> Tool | None:
    """Parse a single line like  bash:/usr/bin/env bash -c "{command}" """
    line = raw.strip()
    if not line or line.startswith("#"):
        return None

    # Extract optional description comment (#! ...)
    description = ""
    if "#!" in line:
        line, description = line.split("#!", 1)
        line = line.strip()
        description = description.strip()

    if ":" not in line:
        return None

    name, template = line.split(":", 1)
    name = name.strip()
    template = template.strip()

    params = extract_fstring_params(template)
    return Tool(name=name, template=template, params=params, description=description)


def parse_tools_file(path: str) -> list[Tool]:
    """Parse an entire tools.txt file, skipping blanks/comments."""
    # Handle comment-only or description lines that precede a tool line.
    # Format:
    #   #! Run a shell command
    #   bash:/usr/bin/env bash -c "{command}"
    pending_desc = ""
    tools: list[Tool] = []
    with open(path) as f:
        for raw in f:
            stripped = raw.strip()
            if stripped.startswith("#!") and ":" not in stripped:
                # standalone description comment — save for next tool
                pending_desc = stripped[2:].strip()
                continue
            tool = parse_line(stripped)
            if tool:
                if pending_desc and not tool.description:
                    tool.description = pending_desc
                pending_desc = ""
                tools.append(tool)
            elif stripped.startswith("#"):
                # regular comment, discard pending
                pending_desc = ""
    return tools


# ---------------------------------------------------------------------------
# Code generation (Jinja templates)
# ---------------------------------------------------------------------------
PYTHON_TEMPLATE = '''\
"""Auto-generated MCP tools from {{ source_file }} — do not edit."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("singleline-tools")

{% for tool in tools %}

@mcp.tool(name="{{ tool.name }}", description="{{ tool.description }}")
{% if tool.params %}
async def {{ tool.name | replace("-", "_") }}({{ tool.params | join(", ") }}):
    """{{ tool.description }}"""
    import subprocess
    template = {{ tool.template | tojson }}
    command = template.format({{ tool.py_kwargs }})
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else result.stderr
{% else %}
async def {{ tool.name | replace("-", "_") }}():
    """{{ tool.description }}"""
    import subprocess
    result = subprocess.run({{ tool.template | tojson }}, shell=True, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else result.stderr
{% endif %}

{% endfor %}

if __name__ == "__main__":
    mcp.run()
'''

TYPESCRIPT_TEMPLATE = '''\
// Auto-generated MCP tools from {{ source_file }} — do not edit.

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { spawn } from "child_process";
import util from "util";

const execAsync = util.promisify(spawn);

export const server = new McpServer({
  name: "singleline-tools",
  version: "1.0.0",
});

{% for tool in tools %}
server.tool(
  "{{ tool.name }}",
  "{{ tool.description }}",
{% if tool.params %}
  {
    {{ tool.ts_schema }}
  },
  async ({ {{ tool.params | join(", ") }} }) => {
    const template = {{ tool.template | tojson }};
    const command = template.replace(/\\{(\\w+)\\}/g, (_, key: string) => {
      const map: Record<string, string> = { {{ tool.params | join(", ") }} };
      return map[key] || "";
    });
    // execute command...
    return { content: [{ type: "text", text: command }] };
  }
);
{% else %}
  {},
  async () => {
    const command = {{ tool.template | tojson }};
    return { content: [{ type: "text", text: command }] };
  }
);
{% endif %}

{% endfor %}
'''


def build_ts_schema(params: list[str]) -> str:
    """Build a JSON-schema-like string for TypeScript tool params."""
    lines = []
    for p in params:
        lines.append(f'    {p}: {{ type: "string", description: "The {p} parameter" }},')
    return "\n".join(lines)


def build_kwargs(params: list[str]) -> str:
    """Build keyword args string for str.format(), e.g. 'content=content, path=path'."""
    return ", ".join(f"{p}={p}" for p in params)


def generate(tools: list[Tool], lang: str, source_file: str) -> str:
    """Render tools list into the target language."""
    for t in tools:
        t.ts_schema = build_ts_schema(t.params)
        t.py_kwargs = build_kwargs(t.params)

    env = Environment(loader=DictLoader({
        "python": PYTHON_TEMPLATE,
        "typescript": TYPESCRIPT_TEMPLATE,
    }))
    tmpl = env.get_template(lang)
    return tmpl.render(tools=tools, source_file=source_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Compile a tools.txt spec into MCP tool code."
    )
    parser.add_argument("--mcp", required=True, help="Path to tools.txt spec file")
    parser.add_argument(
        "--lang",
        required=True,
        choices=["python", "typescript"],
        help="Output language",
    )
    parser.add_argument(
        "--output", "-o", help="Output file (default: stdout)"
    )
    args = parser.parse_args()

    if not os.path.isfile(args.mcp):
        print(f"Error: file not found: {args.mcp}", file=sys.stderr)
        sys.exit(1)

    tools = parse_tools_file(args.mcp)
    if not tools:
        print("Warning: no tools found in spec file", file=sys.stderr)
        sys.exit(0)

    output = generate(tools, args.lang, os.path.basename(args.mcp))

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Generated {args.output} with {len(tools)} tool(s)")
    else:
        print(output)


if __name__ == "__main__":
    main()
