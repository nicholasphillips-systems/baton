"""Exercise handoffs, concurrency, recovery, and native launches in disposable folders."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shared-workflow-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.project = self.home / "Projects" / "Example Project"
        self.project.mkdir(parents=True)
        self.env = os.environ.copy()
        self.env.pop("DESK_STATE_DIR", None)
        self.env.pop("SHARED_NOTES_DIR", None)
        self.env["WORKFLOW_USER_HOME"] = str(self.home)
        self.state = self.home / ".local/state/threadline/workspace.json"

    def run_tool(self, name, *arguments, check=True, env=None):
        return subprocess.run([str(ROOT / "bin" / name), *map(str, arguments)],
                              env=env or self.env, cwd=self.project, capture_output=True,
                              text=True, check=check, timeout=20)

    def desk(self, *args, **kwargs):
        return self.run_tool("desk", *args, **kwargs)

    def data(self):
        return json.loads(self.state.read_text())

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.project), *args], text=True).strip()

    def init_git(self):
        self.git("init", "-q")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.invalid")
        (self.project / "example.txt").write_text("committed\n")
        self.git("add", "example.txt")
        self.git("commit", "-qm", "Fixture")

    def test_reads_do_not_create_or_change_state(self):
        self.desk("list"); self.desk("projects"); self.desk("context")
        self.assertFalse(self.state.exists())
        self.desk("start", self.project, "sample", "first")
        before = self.state.read_bytes()
        self.desk("list"); self.desk("projects"); self.desk("context")
        self.assertEqual(self.state.read_bytes(), before)

    def test_start_and_finish_preserve_dirty_git_and_actual_folder(self):
        self.init_git()
        (self.project / "example.txt").write_text("latest unsaved work\n")
        before_head = self.git("rev-parse", "HEAD")
        before_index = (self.project / ".git/index").read_bytes()
        result = self.desk("start", self.project, "work", "first")
        self.assertIn(str(self.project), result.stdout)
        self.desk("done", "work", "Updated wording", "--next", "Review it", "--checks", "Manual review")
        self.assertEqual(self.git("rev-parse", "HEAD"), before_head)
        self.assertEqual((self.project / ".git/index").read_bytes(), before_index)
        self.assertEqual((self.project / "example.txt").read_text(), "latest unsaved work\n")
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)

    def test_handoff_survives_new_processes(self):
        self.desk("add", "example", self.project)
        self.desk("start", "example", "wording", "first")
        self.desk("note", "wording", "Overview written", "--next", "Check Windows", "--checks", "12 checks passed")
        result = self.desk("context", "example").stdout
        self.assertIn("Overview written", result)
        self.assertIn("Check Windows", result)
        self.assertIn("12 checks passed", result)
        self.desk("done", "wording")
        self.assertIn("Overview written", self.desk("context", "example").stdout)

    def test_new_task_does_not_erase_the_previous_handoff(self):
        self.desk("start", self.project, "one", "first")
        self.desk("done", "one", "Important result", "--next", "Review the result")
        self.desk("start", self.project, "two", "second")
        text = self.desk("context", str(self.project)).stdout
        self.assertIn("Important result", text)
        self.assertIn("Review the result", text)

    def test_installer_keeps_native_config_and_links_one_source(self):
        config = self.home / ".codex/config.toml"
        config.parent.mkdir(); config.write_text('model = "user-choice"\n')
        result = subprocess.run([str(ROOT / "install.sh"), "--instructions"], env=self.env,
                                capture_output=True, text=True, check=True, timeout=20)
        self.assertEqual(config.read_text(), 'model = "user-choice"\n')
        self.assertEqual((self.home / ".local/bin/desk").resolve(), ROOT / "bin/desk")
        self.assertEqual((self.home / "CLAUDE.md").read_text(), (self.home / ".codex/AGENTS.md").read_text())
        self.assertFalse(self.state.exists())

    def test_invalid_install_option_makes_no_changes(self):
        result = subprocess.run([str(ROOT / "install.sh"), "--unknown"], env=self.env,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.home / ".local").exists())

    def test_concurrent_registry_updates_are_not_lost(self):
        def launch(i):
            return self.desk("start", self.project, "same task", "worker-" + str(i))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(launch, range(20)))
        data = self.data()
        self.assertEqual(len(data["tasks"]), 20)
        self.assertEqual(len(data["events"]), 20)
        self.assertEqual(len(data["projects"]), 1)

    def test_overlapping_work_is_advisory(self):
        self.desk("start", self.project, "one", "first")
        result = self.desk("start", self.project, "two", "second")
        self.assertIn("Heads up", result.stdout)
        self.assertEqual(len(self.data()["tasks"]), 2)

    def test_native_worktrees_share_project_identity(self):
        self.init_git()
        secondary = self.home / "native-worktree"
        self.git("worktree", "add", "-qb", "parallel", str(secondary))
        self.desk("start", self.project, "one", "first")
        self.desk("start", secondary, "two", "second")
        data = self.data()
        self.assertEqual(len(data["projects"]), 1)
        self.assertEqual(data["tasks"]["two"]["path"], str(secondary))
        self.assertIn(str(secondary), self.desk("context", self.project).stdout)

    def test_pause_keeps_files_and_resume_is_explicit(self):
        marker = self.project / "keep.txt"; marker.write_text("keep")
        self.desk("start", self.project, "one", "first")
        self.desk("pause", "one", "Paused", "--next", "Continue tomorrow")
        self.assertEqual(self.data()["tasks"]["one"]["status"], "paused")
        self.assertEqual(marker.read_text(), "keep")
        self.desk("note", "one", "More detail")
        self.assertEqual(self.data()["tasks"]["one"]["status"], "paused")
        self.desk("resume", "one", "Resumed")
        self.assertEqual(self.data()["tasks"]["one"]["status"], "active")

    def test_finish_saves_a_plain_language_result(self):
        self.desk("start", self.project, "one", "first")
        self.desk("done", "one", "Finished")
        self.assertEqual(self.data()["tasks"]["one"]["status"], "done")


    def test_corrupt_state_is_not_silently_replaced(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text("broken state")
        result = self.desk("start", self.project, "one", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state.read_text(), "broken state")

    def test_previous_state_is_available_for_recovery(self):
        self.desk("start", self.project, "one", "first")
        first = self.state.read_bytes()
        self.desk("note", "one", "New status")
        self.assertEqual((self.state.parent / "workspace.previous.json").read_bytes(), first)

    def test_unregistered_project_does_not_receive_another_project_handoff(self):
        self.desk("start", self.project, "one", "first")
        self.desk("note", "one", "unrelated-project-result")
        other = self.home / "Other"; other.mkdir()
        self.assertNotIn("unrelated-project-result", self.desk("context", other).stdout)


    def test_map_skips_private_and_generated_trees(self):
        (self.project / "visible.txt").write_text("content")
        for name in ["graphify-out", "node_modules", ".git", ".claude"]:
            p = self.project / name; p.mkdir(); (p / "secret-name.txt").write_text("dummy")
        private = self.home / "Private"; private.mkdir(); (private / "vault.txt").write_text("dummy")
        self.run_tool("map", "update")
        index = (self.home / ".map/files.txt").read_text()
        self.assertIn("visible.txt", index)
        self.assertNotIn("secret-name", index)
        self.assertNotIn("vault.txt", index)

    def test_mem_searches_shared_notes_not_native_memories(self):
        shared = self.home / "Documents/Threadline/Systems"; shared.mkdir(parents=True)
        (shared / "Sample.md").write_text("# Sample\nshared-test-marker")
        private = self.home / ".claude/projects/-home-example/memory"; private.mkdir(parents=True)
        (private / "private.md").write_text("private-test-marker")
        self.assertIn("Sample.md", self.run_tool("mem", "shared-test-marker").stdout)
        self.assertNotIn("private.md", self.run_tool("mem", "private-test-marker").stdout)

    def test_default_command_lists_tasks(self):
        self.assertIn("No open tasks", self.desk().stdout)
        self.desk("start", self.project, "one", "first")
        self.assertIn("one | active", self.desk().stdout)

    def test_notes_do_not_reopen_finished_work(self):
        self.desk("start", self.project, "one", "first")
        self.desk("done", "one", "Finished")
        self.desk("note", "one", "Added test details", "--checks", "Verified")
        self.assertEqual(self.data()["tasks"]["one"]["status"], "done")
        self.assertNotIn("one |", self.desk("list").stdout)
        self.assertIn("one | done", self.desk("list", "--all").stdout)
        self.assertIn("Added test details", self.desk("show", "one").stdout)

    def test_paused_tasks_remain_visible_in_project_context(self):
        self.desk("start", self.project, "one", "first")
        self.desk("pause", "one", "Need a decision", "--next", "Choose the title")
        text = self.desk("context", self.project).stdout
        self.assertIn("one | paused", text)
        self.assertIn("Choose the title", text)

    def test_list_can_select_a_project(self):
        other = self.home / "Other Project"; other.mkdir()
        self.desk("start", self.project, "one", "first")
        self.desk("start", other, "two", "second")
        text = self.desk("list", "--project", self.project).stdout
        self.assertIn("one | active", text)
        self.assertNotIn("two | active", text)

    def test_repeated_start_is_a_read_only_noop(self):
        self.desk("start", self.project, "one", "first")
        before = self.state.read_bytes(); changed = self.state.stat().st_mtime_ns
        self.desk("start", self.project, "one", "first")
        self.assertEqual(self.state.read_bytes(), before)
        self.assertEqual(self.state.stat().st_mtime_ns, changed)
        self.assertFalse((self.state.parent / "workspace.previous.json").exists())

    def test_empty_task_title_is_rejected_without_writing(self):
        result = self.desk("start", self.project, "   ", "first", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.state.exists())

    def test_invalid_nested_records_are_not_overwritten(self):
        self.desk("start", self.project, "one", "first")
        data = self.data(); data["tasks"]["one"]["status"] = "invalid"
        self.state.write_text(json.dumps(data))
        before = self.state.read_bytes()
        result = self.desk("note", "one", "Attempt", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.state.read_bytes(), before)

    def test_invalid_top_level_state_reports_an_error(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text("[]")
        result = self.desk("doctor", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.state.read_text(), "[]")

    def test_detached_checkout_is_reported(self):
        self.init_git(); self.git("checkout", "--detach", "-q")
        text = self.desk("context", self.project).stdout
        self.assertIn("detached HEAD", text)

    def test_home_git_repository_is_not_presented_as_a_project_checkout(self):
        subprocess.run(["git", "init", "-q", str(self.home)], check=True)
        text = self.desk("context", self.project).stdout
        self.assertNotIn("Current Git checkout", text)

    def test_native_launches_do_not_depend_on_shared_state(self):
        config = self.home / ".codex/config.toml"
        config.parent.mkdir(); config.write_text('model = "user-choice"\n')
        self.state.parent.mkdir(parents=True); self.state.write_text("unavailable")
        tools = self.home / ".local/bin"; tools.mkdir(parents=True)
        for name in ["codex", "claude", "gemini"]:
            stub = tools / name
            stub.write_text('#!/bin/sh\nprintf "native-application\\n"\n')
            stub.chmod(0o755)
        env = self.env.copy(); env.pop("WORKSPACE", None)
        env["PATH"] = str(tools) + os.pathsep + env["PATH"]
        before = sorted(f.relative_to(self.home) for f in self.home.rglob("*"))
        for name in ["codex", "claude", "gemini"]:
            result = self.run_tool("launch-ai", name, "--in-terminal", env=env)
            self.assertEqual(result.stdout.strip(), "native-application")
            self.assertEqual(result.stderr, "")
        self.assertEqual(config.read_text(), 'model = "user-choice"\n')
        self.assertEqual(self.state.read_text(), "unavailable")
        self.assertEqual(sorted(f.relative_to(self.home) for f in self.home.rglob("*")), before)

    def test_map_search_does_not_build_or_refresh_its_cache(self):
        self.run_tool("map", "example")
        index = self.home / ".map/files.txt"
        self.assertFalse(index.exists())
        self.run_tool("map", "update")
        before = index.read_bytes()
        (self.project / "new-result.txt").write_text("new")
        self.assertNotIn("new-result.txt", self.run_tool("map", "new-result").stdout)
        self.assertEqual(index.read_bytes(), before)
        self.run_tool("map", "update")
        self.assertIn("new-result.txt", self.run_tool("map", "new-result").stdout)

    def test_map_can_remove_a_description_after_the_folder_is_gone(self):
        folder = self.home / "Documents/Temporary"; folder.mkdir(parents=True)
        self.run_tool("map", "note", folder, "Temporary reference")
        folder.rmdir()
        self.assertNotEqual(self.run_tool("map", "doctor", check=False).returncode, 0)
        self.run_tool("map", "forget", folder)
        self.assertEqual(self.run_tool("map", "doctor").returncode, 0)
        self.assertNotIn("Temporary reference", (self.home / ".map/notes.tsv").read_text())

    def test_mem_history_is_explicit(self):
        notes = self.home / "Documents/Threadline"
        for folder in ["Systems", "Runs"]:
            (notes / folder).mkdir(parents=True)
        (notes / "Systems/Current.md").write_text("# Current\nshared-example-marker")
        (notes / "Runs/Past.md").write_text("# Past\nshared-example-marker")
        (notes / "Systems/Old.md").write_text("---\nstatus: archived\n---\nshared-example-marker")
        current = self.run_tool("mem", "shared-example-marker").stdout
        self.assertIn("Current.md", current)
        self.assertNotIn("Past.md", current); self.assertNotIn("Old.md", current)
        historical = self.run_tool("mem", "--history", "shared-example-marker").stdout
        self.assertIn("Past.md", historical); self.assertIn("Old.md", historical)

    def test_custom_launcher_preserves_arguments_without_shell_evaluation(self):
        arguments = ["two words", "$(touch should-not-exist)", "x; echo unexpected"]
        script = "import json,os,sys; print(json.dumps([os.getcwd(),sys.argv[1:]]))"
        result = self.run_tool("launch-ai", "--exec", "Example tool", "--", sys.executable,
                               "-c", script, *arguments)
        folder, actual = json.loads(result.stdout)
        self.assertEqual(folder, str(self.project))
        self.assertEqual(actual, arguments)
        self.assertFalse((self.project / "should-not-exist").exists())
        self.assertFalse(self.state.exists())

    def test_launcher_uses_selected_workspace(self):
        selected = self.home / "Another project with spaces"; selected.mkdir()
        env = self.env.copy(); env["WORKSPACE"] = str(selected)
        result = self.run_tool("launch-ai", "--exec", "Example", "--", sys.executable,
                               "-c", "import os; print(os.getcwd())", env=env)
        self.assertEqual(result.stdout.strip(), str(selected))

    def test_unknown_launcher_application_fails_without_creating_state(self):
        result = self.run_tool("launch-ai", "missing-example-app", check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown application", result.stderr)
        self.assertFalse(self.state.exists())

    def test_map_roots_select_only_requested_work_folders(self):
        research = self.home / "Research"; research.mkdir()
        (research / "selected.txt").write_text("example")
        (self.project / "other.txt").write_text("example")
        env = self.env.copy(); env["MAP_ROOTS"] = "Research"
        self.run_tool("map", "update", env=env)
        index = (self.home / ".map/files.txt").read_text()
        self.assertIn("Research/selected.txt", index)
        self.assertNotIn("other.txt", index)

    def test_map_roots_cannot_escape_workflow_home(self):
        env = self.env.copy(); env["MAP_ROOTS"] = "../outside"
        result = self.run_tool("map", "update", env=env, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("relative to the workflow home", result.stderr)
        self.assertFalse((self.home / ".map/files.txt").exists())


if __name__ == "__main__":
    unittest.main()
