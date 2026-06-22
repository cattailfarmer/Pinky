# Swarm Codex MVP Plan

## Goal

Build a local inspectable worker system that an outer Codex conversation can supervise.

## Phase 1: Durable Records

- Create `.swarm/` layout.
- Define `session.json`, `task.json`, `run.json`, and `transcript.jsonl`.
- Implement a minimal CLI that can create sessions, tasks, and run folders.
- Capture worker stdout/stderr to `terminal.log`.

## Phase 2: One Worker Adapter

Preferred first adapter: Codex CLI app-server with a dedicated `CODEX_HOME` and LM Studio/OSS config.

Fallback adapter: opencode or aider with output capture.

Acceptance criteria:

- Worker can start from a task file.
- Worker output is captured in a run folder.
- Worker can produce a summary.
- Worker can produce a patch or explicitly say no patch was made.

## Phase 3: Local Dashboard

Serve a local web page:

```text
http://127.0.0.1:8787/sessions/<session-id>
```

Minimum UI:

- Session title/status.
- Task list.
- Run list.
- Transcript/log viewer.
- Artifact links.
- Patch viewer.

## Phase 4: Codex Supervision Loop

Outer Codex should be able to:

- Write task specs.
- Start local workers.
- Inspect run artifacts.
- Review patches.
- Apply accepted changes.
- Record final disposition.

## Non-Goals For MVP

- No complex multi-agent scheduling.
- No autonomous write-heavy swarm.
- No cloud hosting.
- No polished IDE integration.
- No multi-user auth.
- No automatic patch application without review.

