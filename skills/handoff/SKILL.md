---
name: handoff
description: Save a handoff so the next session or another AI agent can continue this work. Use when the user says "save a handoff", "wrap up", "pause this", "done for now", is about to switch agents, or at the end of substantial work. Records what changed, what was checked and the next step with desk.
---

# Leave the next session a handoff

`desk` is on `PATH` while this plugin is enabled.

1. **Find the task ID.** Use the ID `desk start` printed, or look it up with `desk list`. If no task was started for this work, run `desk start <project-or-folder> "<task>" claude` first.
2. **Save the right kind of handoff:**
   - Checkpoint, still working: `desk note <task> "<what changed>" --checks "<what was verified>" --next "<next step>"`
   - Stopping unfinished: `desk pause <task> "<where it stopped>" --next "<next step>"`
   - Finished: `desk done <task> "<result>" --checks "<what was verified>" --next "<remaining work, or None>"`
3. **Write for a reader with no memory of this session.** Name the files, commands and decisions. Record only the checks that actually ran, and say plainly when something was not verified.
4. **Keep secrets out.** Never put credentials, tokens or private conversation content in a handoff.
5. **Leave Git alone.** A handoff never commits, pushes or changes Git. Do Git work only when the user asks for it.

Finish by telling the user in one line what was saved and the next step it records.
