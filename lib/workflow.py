"""Shared task status and project handoffs. Git and project files are read-only."""

import contextlib
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


class WorkflowError(Exception):
    pass


def user_home():
    return Path(os.environ.get("WORKFLOW_USER_HOME", Path.home())).expanduser().resolve()


def state_dir():
    return Path(os.environ.get("DESK_STATE_DIR", user_home() / ".local/state/threadline")).expanduser().resolve()


def notes_dir():
    return Path(os.environ.get("SHARED_NOTES_DIR", user_home() / "Documents/Threadline")).expanduser()


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")


def local_time(value):
    return datetime.datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def slug(text):
    return re.sub(r"[^a-z0-9._-]+", "-", text.lower()).strip("-.") or "task"


def clean(text):
    return " ".join(str(text or "").split())[:2000]


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load():
    path = state_dir() / "workspace.json"
    if not path.exists():
        return {"version": 1, "projects": {}, "tasks": {}, "events": []}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise WorkflowError(f"Cannot read {path}: {error}. Existing state was not replaced.") from error
    if not isinstance(data, dict) or data.get("version") != 1 or not all(isinstance(data.get(k), t) for k, t in
                                          [("projects", dict), ("tasks", dict), ("events", list)]):
        raise WorkflowError(f"Invalid workspace state in {path}; restore a valid recovery copy.")
    def require(condition):
        if not condition:
            raise ValueError("Invalid record")

    try:
        for key, project in data["projects"].items():
            require(isinstance(project, dict) and Path(project["path"]).is_absolute())
            require(isinstance(project["aliases"], list) and all(isinstance(a, str) for a in project["aliases"]))
            saved = project.get("handoff")
            if saved is not None:
                require(isinstance(saved, dict) and saved["id"] in data["tasks"])
                require(data["tasks"][saved["id"]]["project"] == key)
                require(all(isinstance(saved[k], str) for k in ["id", "owner", "path", "summary", "next", "checks", "status", "updated"]))
                require(saved["status"] in {"active", "paused", "done"})
                datetime.datetime.fromisoformat(saved["updated"])
        for task_id, task in data["tasks"].items():
            require(task["id"] == task_id and task["project"] in data["projects"])
            require(task["status"] in {"active", "paused", "done"})
            require(all(isinstance(task[k], str) for k in ["title", "owner", "path", "summary", "next", "checks", "updated"]))
            require(Path(task["path"]).is_absolute())
            datetime.datetime.fromisoformat(task["updated"])
        for entry in data["events"]:
            require(all(isinstance(entry[k], str) for k in ["at", "action", "task", "project", "owner", "summary", "next", "checks", "path"]))
            datetime.datetime.fromisoformat(entry["at"])
    except (AssertionError, KeyError, TypeError, ValueError) as error:
        raise WorkflowError(f"Invalid records in {path}; existing state was not replaced.") from error
    return data


@contextlib.contextmanager
def transaction():
    folder = state_dir()
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "workspace.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = load()
        before = json.dumps(data, sort_keys=True, ensure_ascii=False)
        yield data
        if json.dumps(data, sort_keys=True, ensure_ascii=False) == before:
            return
        current = folder / "workspace.json"
        if current.exists():
            atomic_write(folder / "workspace.previous.json", current.read_text())
        atomic_write(folder / "workspace.json", json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def git_read(path, *args):
    try:
        result = subprocess.run(["git", "--no-optional-locks", "-C", str(path), *args],
                                capture_output=True, text=True, timeout=3)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def canonical(path):
    """Associate native Git worktrees with their main repository without modifying either."""
    path = Path(path).expanduser().resolve()
    common = git_read(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common:
        common_path = Path(common)
        if common_path.name == ".git" and common_path.parent != user_home():
            return common_path.parent.resolve()
    return path


def project_for(data, query):
    query = str(query)
    for key, project in data["projects"].items():
        if query == key or query in project.get("aliases", []):
            return key, Path(project["path"])
    path = Path(query).expanduser().resolve()
    if not path.is_dir():
        raise WorkflowError(f"Unknown project or folder: {query}. Use desk projects or a real folder path.")
    primary = canonical(path)
    matches = [(key, p) for key, p in data["projects"].items()
               if primary == Path(p["path"]) or path.is_relative_to(Path(p["path"]))]
    if matches:
        key, _ = max(matches, key=lambda item: len(item[1]["path"]))
        return key, path
    return None, path


def ensure_project(data, query, name=None):
    key, actual = project_for(data, query)
    if key:
        if name and name != key and name not in data["projects"][key]["aliases"]:
            if name in data["projects"] or any(name in p["aliases"] for p in data["projects"].values()):
                raise WorkflowError(f"Project alias already exists: {name}")
            data["projects"][key]["aliases"].append(name)
        return key, actual
    primary = canonical(actual)
    base = slug(name or primary.name)
    key = base
    counter = 2
    while key in data["projects"] or any(key in p["aliases"] for p in data["projects"].values()):
        key = f"{base}-{counter}"
        counter += 1
    data["projects"][key] = {"path": str(primary), "aliases": [], "handoff": None}
    return key, actual


def event(data, action, task):
    data["events"].append({"at": timestamp(), "action": action, "task": task["id"],
                           "project": task["project"], "owner": task["owner"],
                           "summary": task["summary"], "next": task.get("next", ""),
                           "checks": task.get("checks", ""), "path": task["path"]})


def handoff(data, task):
    data["projects"][task["project"]]["handoff"] = {
        k: task[k] for k in ["id", "owner", "path", "summary", "next", "checks", "status", "updated"]}


def start(query, title, owner):
    title, owner = clean(title), clean(owner)
    if not title or not owner:
        raise WorkflowError("Give the task a title and an owner.")
    with transaction() as data:
        key, actual = ensure_project(data, query)
        if not actual.is_dir():
            raise WorkflowError(f"Project folder is missing: {actual}")
        for task in data["tasks"].values():
            if (task["status"] == "active" and task["project"] == key and task["title"] == clean(title)
                    and task["owner"] == clean(owner) and task["path"] == str(actual)):
                return task.copy(), []
        others = [t.copy() for t in data["tasks"].values()
                  if t["status"] == "active" and (actual.is_relative_to(Path(t["path"]))
                                                or Path(t["path"]).is_relative_to(actual))]
        base = slug(title)[:80].rstrip("-.")
        task_id = base
        counter = 2
        while task_id in data["tasks"]:
            task_id = f"{base}-{counter}"
            counter += 1
        task = {"id": task_id, "project": key, "title": clean(title), "owner": clean(owner),
                "path": str(actual), "status": "active", "summary": clean(title),
                "next": "", "checks": "", "updated": timestamp()}
        data["tasks"][task_id] = task
        event(data, "started", task)
        return task.copy(), others


def update_task(task_id, summary=None, next_step=None, checks=None, status=None):
    with transaction() as data:
        if task_id not in data["tasks"]:
            raise WorkflowError(f"Unknown task: {task_id}")
        task = data["tasks"][task_id]
        if summary is not None:
            task["summary"] = clean(summary)
        if next_step is not None:
            task["next"] = clean(next_step)
        if checks is not None:
            task["checks"] = clean(checks)
        if status is not None:
            task["status"] = status
        task["updated"] = timestamp()
        handoff(data, task)
        event(data, {None: "updated", "active": "resumed", "done": "finished", "paused": "paused"}[status], task)
        return task.copy()


def render(query=None):
    data = load()
    key = None
    actual = None
    if query is not None:
        key, actual = project_for(data, query)
    lines = ["# Shared workspace context", "", f"Read at: {local_time(timestamp())}", "",
             "Status is recorded by agents, not inferred from open windows. Check the project files before continuing.", "",
             "## Open tasks", ""]
    tasks = [t for t in data["tasks"].values() if t["status"] in {"active", "paused"} and (query is None or t["project"] == key)]
    for task in tasks:
        lines.extend([f"- {task['id']} | {task['status']} | {task['owner']} | {task['path']}",
                      f"  {task['summary']} (updated {local_time(task['updated'])})"])
        if task["next"]:
            lines.append(f"  Next: {task['next']}")
    if not tasks:
        lines.append("- No open tasks registered. The board records updates; it does not monitor processes.")
    lines.extend(["", "## Project handoffs", ""])
    projects = [(k, p) for k, p in data["projects"].items() if query is None or k == key]
    projects.sort(key=lambda item: (item[1].get("handoff") or {}).get("updated", ""), reverse=True)
    if query is None:
        projects = [item for item in projects if item[1].get("handoff")][:6]
    for name, project in projects:
        lines.extend([f"### {name}", f"Folder: {project['path']}"])
        saved = project.get("handoff")
        if saved:
            lines.extend([f"Last recorded: {local_time(saved['updated'])} by {saved['owner']} ({saved['status']})",
                          f"Work folder: {saved['path']}", f"Status: {saved['summary']}",
                          f"Next: {saved['next'] or 'Not recorded.'}",
                          f"Reported checks: {saved['checks'] or 'Not recorded.'}", ""])
        else:
            lines.extend(["No handoff recorded yet. Read the project and dated reference notes.", ""])
    if not projects:
        lines.extend(["No handoff recorded for this selection yet.", ""])
    if actual is not None and git_read(actual, "rev-parse", "--show-toplevel") not in {None, str(user_home())}:
        branch = git_read(actual, "branch", "--show-current")
        if branch is not None:
            changes = git_read(actual, "status", "--porcelain", "--", ".")
            lines.extend(["## Current Git checkout", f"Branch: {branch or 'detached HEAD'}",
                          f"Changed entries: {len(changes.splitlines()) if changes is not None else 'unavailable'}", ""])
            worktrees = git_read(actual, "worktree", "list", "--porcelain")
            work_paths = [line.removeprefix("worktree ") for line in (worktrees or "").splitlines()
                          if line.startswith("worktree ")]
            if work_paths:
                lines.append("Git workspaces (not a claim that they are active):")
                lines.extend("- " + path for path in work_paths)
                lines.append("")
    lines.extend([f"Shared state: {state_dir() / 'workspace.json'}",
                  f"Reference notes: {notes_dir()} (dated background, not the live task board)", ""])
    return "\n".join(lines)
