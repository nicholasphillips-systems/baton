# Changelog

## 0.2.0

- Renamed from Threadline to Baton. Default state is now `~/.local/state/baton` and default notes `~/Documents/Baton`; set `DESK_STATE_DIR` and `SHARED_NOTES_DIR` to keep existing folders.
- Installs as a Claude Code plugin: `desk`, `map` and `mem` on Claude's `PATH`, plus `/baton:pickup` and `/baton:handoff` skills. No hooks, no network calls.
- `launch-ai` moved to `desktop/` so the plugin doesn't put a desktop launcher on Claude's `PATH`. `install.sh` still links it.
- A project registered at the home folder no longer absorbs other projects or unregistered folders beneath it.

## 0.1.0

- Shared project and task records with explicit notes, pause, resume and completion.
- Handoffs that persist across sessions, tools and project switches.
- File-path search and shared Markdown reference search.
- Portable native application launcher and custom-command entrypoint.
- Locked, validated, atomic registry writes with a previous-copy recovery file.
- Generic instructions, configurable work-folder roots and an isolated three-day example.
- Linux CI, contributor guidance and PNG badges.
