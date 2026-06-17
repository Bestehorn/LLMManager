# Credentials

This directory holds local git-host credentials. **Everything here except `*.template`
and this README is gitignored** (see `.gitignore`).

## GitHub PAT

`scripts/github_wrapper.py` reads a GitHub Personal Access Token from
`credentials/github-pat.txt` (one line, no quotes).

1. Create a fine-grained or classic PAT at <https://github.com/settings/tokens> with at
   least `repo` and `workflow` scopes (and `read:org` if needed for the
   `Bestehorn/LLMManager` repo).
2. Copy the template and paste your token:
   ```bash
   cp credentials/github-pat.txt.template credentials/github-pat.txt
   # then edit credentials/github-pat.txt and replace PASTE_YOUR_GITHUB_PAT_HERE
   ```
3. Verify (once the wrapper subcommands are implemented):
   ```bash
   venv\Scripts\activate & python scripts/github_wrapper.py list-workflows
   ```

Never commit `github-pat.txt`. The owner/repo are auto-detected from `.git/config` — do
not hardcode them.
