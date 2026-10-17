---
name: pickup
description: Pick up a project where the last session or another AI agent left off. Use when starting work in a project, or when the user says "pick up", "continue", "where were we", "what was I doing on X", or comes over from another agent. Reads the saved Baton handoff and open tasks, then checks them against the real files.
---

# Pick up where the last session stopped

`desk`, `map` and `mem` are on `PATH` while this plugin is enabled.

1. **Find the project.** Use the current folder when it is the project. Otherwise run `desk projects`, or `map <words>` to find a folder by name or description.
2. **Read the handoff.** Run `desk context <project-or-folder>`, using `.` for the current folder. With no argument it gives an overview of recent projects instead. It prints open tasks, the last saved status, the next step, the checks that were run, and a read-only Git summary.
3. **Check for other agents.** Run `desk list`. If another agent has an open task in the same folder, coordinate with the user instead of overwriting its work.
4. **Verify before trusting.** A handoff is what the last session reported, not proof. Look at the files, tests or Git state it mentions before relying on it.
5. **Register the work.** Run `desk start <project-or-folder> "<task>" claude` and keep the task ID it prints for the handoff later. Repeating the same start is harmless.
6. **Report briefly.** Tell the user in two or three lines where it stood, what the next step was, and anything that no longer matches the files.

If `desk context` shows no handoff for the folder, this is the first session there; `desk start` registers the folder.

`mem <words>` searches shared Markdown notes (`SHARED_NOTES_DIR`, default `~/Documents/Baton`) and current handoffs. Add `--history` to include completed runs.
