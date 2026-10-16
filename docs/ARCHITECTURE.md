# Architecture

Threadline is a set of local commands. Agents read shared project records and leave explicit handoffs. There is no background service or provider-specific conversation store.

| Source | Responsibility |
| --- | --- |
| `lib/workflow.py` | Project identity, registry validation, locking, updates and context rendering |
| `bin/desk` | Project and task command line |
| `bin/map` | Explicit indexing and path/description search |
| `bin/mem` | Shared Markdown and latest-handoff search |
| `bin/launch-ai` | Native application dispatch in a selected working folder |
| `install.sh` | Link four commands; optionally install instructions |
| `scripts/configure-workflow.py` | Install generic instructions, backing up replacements |

## Task records and sessions

The registry defaults to `~/.local/state/threadline/workspace.json`. Its three collections are `projects`, `tasks` and `events`. Each project also stores its latest handoff.

A task records its ID, title, project, owner, actual working path, status, summary, next action, checks and update time. Updates copy those fields into the project's handoff and append an event. Status is explicitly `active`, `paused` or `done`; notes retain the current status.

Writes hold a file lock, validate existing records and atomically replace the registry. `workspace.previous.json` retains the prior valid version. Identical starts avoid a write. Malformed state is reported rather than silently replaced.

An agent reads `desk context <project>` and actual files, registers work, makes and verifies changes, then records the outcome and next action. A later session repeats the read step. Each project's handoff remains separate. [The example](EXAMPLE.md) follows three projects over successive sessions.

Context includes active and paused work, the latest handoff and read-only Git checkout information. Native worktrees share project identity while tasks preserve their actual working paths. Git inspection creates no branches or commits.

The latest handoff reflects the most recently updated task, including updates to older tasks. Full records remain available through `desk show` and `desk list --all`. The board does not monitor processes, block edits or save when a window closes. Agents coordinate and record progress explicitly.

## Search

`map update` writes `~/.map/files.txt` and a generated `MAP.md`; descriptions live in `notes.tsv`. `MAP_ROOTS` selects folders relative to the workflow home, defaulting to `Projects:Documents`. Hidden folders, symlinks, common dependencies, private/vault folders and generated graphs are skipped.

Search matches names and descriptions rather than contents. File changes require explicit refresh; `map doctor` checks described locations rather than every cached path. The cache is a convenience, not a place to store secrets.

`mem` reads Markdown files directly in the shared root and selected categories. History mode adds `Runs` and archived references. Matching notes and latest project handoffs are ranked. Nested note folders are not searched. An invalid registry currently also stops note-search output. Private application histories are not indexed.

Project files establish implemented behavior, task records carry reported work, and notes hold reusable explanations and decisions.

## Installation and launching

Installation links only `desk`, `map`, `mem` and `launch-ai`. Optional `--instructions` installs `~/AGENTS.md` and pointers at `~/CLAUDE.md`, `~/GEMINI.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, `~/.qwen/QWEN.md`, `~/.config/opencode/AGENTS.md`, `~/.cursorrules` and `~/.clinerules`. Existing files are backed up; this replaces rather than merges. Review templates before using the option.

The launcher runs installed commands in `WORKSPACE`, defaulting to the current folder. CLI apps can use a detected terminal or the caller's terminal. Custom `--exec` arguments are passed as an array without shell evaluation. Launching does not read task state, inject context, change provider settings or start remote-machine adapters.

Configuration is listed in the [README](../README.md). Native applications keep their own models, credentials and settings.
