# Read Complete Command Output

When running a shell command, never truncate, tail, head, or paginate its output. You
must see the whole thing to reason about it correctly — a tail can hide the error that
matters.

Forbidden patterns (do not append these to commands whose output you need to analyze):
- `| tail`, `| head`
- `| Select-Object -First`, `| Select-Object -Last` (PowerShell)
- `| more`, `| less`
- `2>&1 | tail -n` and similar
- redirecting to a file and then reading only part of it

If output is genuinely enormous (e.g. a full test run), prefer flags that make the tool
itself concise (`pytest --tb=short`, `-q` only when you do not need the detail) rather
than piping through a truncator. When you need to grep for a specific line, that is
fine — but never use grep/tail/head as a way to avoid reading a result you are about to
draw a conclusion from.
