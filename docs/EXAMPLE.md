# Three days of shared work

This example follows successive sessions. First an agent works on a project and saves a handoff. A later session reads that handoff before continuing. Other projects can be worked on between those sessions without replacing the first project's saved context.

The days, agents, work and check descriptions below are illustrative. The commands exercise the real task registry; they do not launch agents or create the described website, music or interview outputs.

## Prepare an isolated example

Run these blocks in one shell. They use a temporary workflow home and keep the real task board and notes unchanged. Close that shell when finished to discard the environment overrides.

```bash
workflow_demo_root="$(mktemp -d -t workflow-demo.XXXXXX)"
export WORKFLOW_USER_HOME="$workflow_demo_root"
export DESK_STATE_DIR="$workflow_demo_root/.local/state/threadline"
export SHARED_NOTES_DIR="$workflow_demo_root/Documents/Threadline"
mkdir -p "$workflow_demo_root/Projects/Website" \
  "$workflow_demo_root/Projects/Music" \
  "$workflow_demo_root/Projects/Interview"
desk add website "$workflow_demo_root/Projects/Website"
desk add music "$workflow_demo_root/Projects/Music"
desk add interview "$workflow_demo_root/Projects/Interview"
```

## Day 1: work, save, then switch projects

Claude drafts a website page and records the next action before the session ends. Later, Gemini records music options and pauses for a decision. After that, Codex leaves interview questions for the next practice session.

```bash
desk start website "Draft contact page" claude
desk done draft-contact-page "Contact page draft saved" \
  --checks "Example: local page reviewed" --next "Verify form delivery"

desk start music "Choose arrangement" gemini
desk pause choose-arrangement "Options A and B saved" \
  --checks "Example: both options reviewed" --next "User chooses A or B"

desk start interview "Prepare questions" codex
desk done prepare-questions "Practice questions saved" \
  --checks "Example: role topics covered" --next "Practice answers"
```

All three handoffs now exist separately. The website session has ended; its next action remains available while the other work happens.

## Day 2: read the earlier work before continuing

Codex returns to the website first. `desk context website` returns Claude's saved result and the instruction to verify delivery. Codex records that a provider decision is needed. Later, Gemini reads the music handoff, receives the user's choice of A, and explicitly resumes the paused task. After that, the interview session starts from Codex's saved question list.

```bash
desk context website
desk start website "Verify form delivery" codex
desk pause verify-form-delivery "Waiting for an email provider choice" \
  --checks "Example: form handler inspected" --next "User chooses provider"

desk context music
desk resume choose-arrangement "User chose option A"
desk done choose-arrangement "Option A arrangement saved" \
  --checks "Example: arrangement reviewed" --next "Prepare preview"

desk context interview
desk start interview "Practice answers" gemini
desk done practice-answers "Practice notes saved" \
  --checks "Example: answers reviewed" --next "Write feedback"
```

## Day 3: preserve the pending decision and continue the other work

Codex reads the website handoff and sees that the provider choice is still outstanding. The task stays paused. Later, Claude reads the music handoff and begins a preview task. After that, Gemini reads the interview practice notes and records the completed feedback.

```bash
desk context website
desk note verify-form-delivery "Provider decision still pending" \
  --checks "Example: decision checked" --next "User chooses provider"

desk context music
desk start music "Prepare preview" claude
desk note prepare-preview "Preview plan saved" \
  --checks "Example: arrangement inputs reviewed" --next "Render and listen"

desk context interview
desk start interview "Write feedback" gemini
desk done write-feedback "Feedback saved" \
  --checks "Example: feedback reviewed" --next "None"

desk list
```

The open board now shows `verify-form-delivery` as **paused / codex** and `prepare-preview` as **active / claude**. Interview work is **done / gemini** and appears with `desk list --all` or `desk show write-feedback`.

Persistence comes from recorded task fields, project files and shared notes. The next agent reads them explicitly. The board cannot prove that an application is still running, and a saved report does not replace checking the actual files.
