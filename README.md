# singleline

`singleline` is a compiler that transforms a simple text-based specification file into fully functional Model Context Protocol (MCP) server definitions in either Python or TypeScript.

It allows you to define shell-based tools using a concise "single-line" syntax, removing the boilerplate of manually writing server wrappers for every CLI utility you want to expose to an LLM.

## 🚀 Features

- **Declarative Tooling**: Define tools as simple `name:command` pairs.
- **Parameter Extraction**: Automatically detects `{placeholders}` in your commands and converts them into MCP tool arguments.
- **Multi-language Support**: Generate code for both `FastMCP` (Python) and the `@modelcontextprotocol/sdk` (TypeScript).
- **Documentation**: Support for inline and standalone descriptions using the `#!` prefix.

## 🛠 Installation

Ensure you have Python 3.x installed. You will need the `jinja2` library for code generation:

```bash
pip install jinja2
```

## 📖 Usage

### 1. Create a `tools.txt` spec
Create a text file where each line represents a tool. Use `{variable}` for parameters and `#!` for descriptions.

**Example `tools.txt`:**
```text
#! List files in a directory
ls:ls -la {path}

#! Check system uptime
uptime:uptime

#! Run a custom bash command
bash: /usr/bin/env bash -c "{command}"
```

### 2. Compile to Python
To generate a Python server using `FastMCP`:

```bash
python singleline.py --mcp tools.txt --lang python > tools.py
```

### 3. Compile to TypeScript
To generate a TypeScript server:

```bash
python singleline.py --mcp tools.txt --lang typescript > tools.ts
```

## ⚙️ Command Line Arguments

| Argument | Short | Required | Description |
|-----------|------|----------|-------------|
| `--mcp` | | Yes | Path to the `tools.txt` specification file. |
| `--lang` | | Yes | Target language: `python` or `typescript`. |
| `--output`| `-o` | No | Output file path (defaults to stdout). |

## 🔍 Spec Format Details

- **Tool Definition**: `name:command`
- **Parameters**: Any word inside curly braces `{like_this}` in the command string becomes a tool input.
- **Descriptions**: 
    - **Inline**: `name:command #! Description here`
    - **Standalone**: Place `#! Description here` on the line immediately preceding the tool definition.
- **Comments**: Lines starting with `#` (that are not `#!`) are ignored.

## 📦 Requirements for Generated Code

### Python
The generated `tools.py` requires:
- `mcp` (FastMCP)

### TypeScript
The generated `tools.ts` requires:
- `@modelcontextprotocol/sdk`
- Node.js environment with `child_process` and `util` modules.
