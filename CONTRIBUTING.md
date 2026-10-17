# Contributing to Baton

Small, focused improvements are welcome. Open an issue with the problem and expected behavior, or submit a pull request describing the change and checks run.

Requirements: Linux, Python 3.10+, Bash, Git and ShellCheck. The core has no third-party Python dependencies.

```bash
python3 -m unittest discover -s tests -v
shellcheck -S warning install.sh desktop/launch-ai
git diff --check
```

Tests isolate workflow state and use stub applications. Add regression coverage for changes to registry writes, handoffs, status, search scope or launching. Keep real task boards and paid provider sessions out of test fixtures.

Preserve project files, native settings and explicit status changes. Keep Git actions and indexing opt-in. Preserve malformed data so it can be inspected and recovered.

Use synthetic names, test identities and temporary paths. Exclude personal task records, private notes, credentials, application histories and generated diagrams. Image assets use PNG.
