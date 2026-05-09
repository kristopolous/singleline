
The objective is to have something simpler than toolcall jsons and mcp for 
specifying toolcalls for llms. The insight is to use f-strings and a format
like this:

-- tools.txt --
bash:/usr/bin/env bash -c "{command}"
run-interactive:agent-cli-helper "{command}"
--- 

the idea is that then we can do something like 

oneline (or whatever we call it) --mcp tools.txt --lang python > my-mcp.py

It doesn't really require any token or inference to do, probably. This is all
meta-programming and templates. It can probably be done through jinja so that
typescript and python can both be generated.
