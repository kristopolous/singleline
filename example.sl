#! Run a shell command
bash:/usr/bin/env bash -c "{command}"
#! Run an interactive CLI helper
run-interactive:agent-cli-helper "{command}"
#! Write content to a file
write-file:echo "{content}" > {path}
#! A tool with no params
healthcheck:curl http://localhost:8080/health
