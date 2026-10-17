# Baton

**Pass the work between AI agents without losing your place.**

[![Tests: GitHub Actions](assets/badges/ci.png)](https://github.com/nicholasphillips-systems/baton/actions/workflows/ci.yml)
[![Python 3.10+](assets/badges/python.png)](https://www.python.org/)
[![Platform: Linux](assets/badges/linux.png)](#install)
[![License: MIT](assets/badges/license.png)](LICENSE)

Baton keeps project context available when you return tomorrow or switch AI tools. Work stays in its real folder. Each session saves what changed, what was checked, what is waiting and what should happen next. The next session reads that handoff and continues.

Each project has separate tasks and a saved handoff. Move between projects while keeping track of where each one stands.

| Command | Purpose |
| --- | --- |
| `desk` | Register projects, track tasks and read or save handoffs |
| `map` | Find work-file paths and folder descriptions |
| `mem` | Find shared reference notes and project handoffs |
| `launch-ai` | Open an installed native application in a project folder (Linux desktop, in `desktop/`) |

The core uses the Python standard library. Native applications keep their own models, credentials and settings. Agents explicitly read and save context following shared instructions.

## Install

Requires Linux, Python 3.10+ and Bash. Git provides optional checkout and worktree inspection. Install your preferred AI applications separately.

```bash
git clone https://github.com/nicholasphillips-systems/baton.git
cd baton
./install.sh
export PATH="$HOME/.local/bin:$PATH"
```

The installer links the four commands into `~/.local/bin`. Keep the checkout where you installed it: the links point to its source files. Existing command files are backed up before replacement.

To install the optional shared agent instructions, review `templates/`, then run `./install.sh --instructions`. This replaces `~/AGENTS.md` and the supported instruction entrypoints, backing up existing files under the state directory's `recovery/` folder. Plain installation leaves instruction files alone. Neither mode changes native application settings.

## Claude Code plugin

Baton also installs as a Claude Code plugin. The plugin puts `desk`, `map` and `mem` on Claude's `PATH` and adds two skills, so there is nothing else to install:

```text
/plugin marketplace add nicholasphillips-systems/baton
/plugin install baton@baton
```

| Skill | What it does |
| --- | --- |
| `/baton:pickup` | Reads the project's saved handoff and open tasks, then checks the real files before continuing |
| `/baton:handoff` | Saves what changed, what was checked and the next step, so the next session or another agent can continue |

The plugin has no hooks and makes no network calls. Everything stays in local files: the registry under `~/.local/state/baton/` and, if you use one, the notes folder. Git is read only. It needs Python 3.10+ and is tested on Linux.

## A session and its handoff

Register an existing project folder and start a task:

```bash
desk add website /path/to/your/website
desk context website
desk list
desk start website "Draft contact page" claude
```

Use the task ID printed by `desk start`. A real folder path can replace a registered project name; quote paths containing spaces. After working and checking the result, save a handoff:

```bash
desk pause draft-contact-page "Page drafted; waiting for the delivery provider" \
  --checks "Reviewed the form locally" \
  --next "Choose a provider, then verify form delivery"
```

Later, another session reads the handoff and inspects the actual project files before continuing:

```bash
desk context website
desk show draft-contact-page
desk resume draft-contact-page "Provider selected; continuing verification"
```

Once the work and verification are complete:

```bash
desk done draft-contact-page "Contact page and delivery verified" \
  --checks "Test submission received" --next "None"
```

These are example reports. Record work and checks actually performed. [Try the isolated three-day walkthrough](docs/EXAMPLE.md) to see separate project handoffs surviving successive sessions.

## Task commands

| Command | Effect |
| --- | --- |
| `desk projects` | List registered projects |
| `desk list --project <project>` | Read active and paused tasks for one project |
| `desk list --all` | Include completed tasks |
| `desk note <task> "<result>" --checks "<checks>" --next "<action>"` | Save progress without changing task status |
| `desk pause <task> "<reason>" --next "<action>"` | Mark unfinished work as paused |
| `desk resume <task> "<update>"` | Explicitly reactivate a task |
| `desk done <task> "<result>" --checks "<checks>" --next "<action>"` | Mark complete and save the handoff |
| `desk show <task>` | Read the full task record |
| `desk history` | Read update history |
| `desk doctor` | Check registry records and registered folders |

The board records reported work; it does not monitor processes or block conflicting edits. Coordinate overlapping work directly. Native Git worktrees share project identity while tasks retain their actual working paths. Git commits, merges and cleanup remain explicit actions.

## Files and shared notes

```bash
map update
map contact
map note ~/Projects/website "Website source"
map doctor
mem delivery
mem --history delivery
```

`map` matches cached paths and folder descriptions. Refresh explicitly after files change. `map forget <path>` removes a description. The default roots are `Projects` and `Documents` beneath the workflow home.

`mem` searches Markdown files in the shared note root and its `Projects`, `Systems`, `Knowledge`, `Decisions` and `Inbox` folders, plus current handoffs. `--history` includes `Runs` and archived references. Nested folders are not searched.

## Native launcher

```bash
cd /path/to/your/project
launch-ai claude
launch-ai codex --in-terminal
launch-ai --exec "My editor" -- my-editor .
```

Supported applications: `claude`, `codex`, `gemini`, `qwen`, `kilo`, `opencode`, `hermes`, `devin`, `cursor` and `ollama`. Commands must be on `PATH`. Use `--in-terminal` in an existing terminal, or let the launcher open an available terminal emulator. `--exec` runs another installed command directly; `WORKSPACE` overrides the working folder.

Launching leaves task status and saved context alone. It does not inject handoffs or configure accounts.

## Local state and configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `WORKFLOW_USER_HOME` | Current user's home | Base for workflow paths |
| `DESK_STATE_DIR` | `~/.local/state/baton` | Registry and recovery files |
| `SHARED_NOTES_DIR` | `~/Documents/Baton` | Shared Markdown notes |
| `WORKFLOW_BIN_DIR` | `~/.local/bin` | Installed command links |
| `MAP_ROOTS` | `Projects:Documents` | Colon-separated folders relative to workflow home |
| `DESK_AGENT` | `agent` | Default owner when `desk start` omits one |

`workspace.json` stores projects, tasks, latest handoffs and events. Writes hold a lock, validate records and replace the file atomically. `workspace.previous.json` retains the prior valid version. Read commands and repeated identical starts leave state unchanged. Inspect current and previous files before restoring damaged state.

Personal task data and notes stay outside the repository. See [the architecture and current limits](docs/ARCHITECTURE.md).

## Development

```bash
python3 -m unittest discover -s tests -v
shellcheck -S warning install.sh desktop/launch-ai
git diff --check
```

Tests use temporary homes, disposable Git repositories and stub applications. GitHub Actions tests Python 3.10, 3.12 and 3.14, plus ShellCheck. The PNG badges identify the workflow and environment; live results are available through the CI link.

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md) · [MIT license](LICENSE)
