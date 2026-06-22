# Swarm Codex Specification

## Working Name

Swarm Codex is a local companion system that lets an outer Codex conversation supervise multiple nested coding agents. Each nested agent is inspectable through a local web app that can be loaded in the Codex right-hand panel.

## Core Idea

The outer Codex conversation remains the high-judgment supervisor. It decomposes work, delegates bounded subtasks, reviews results, and performs final integration.

Nested workers run locally, preferably against LM Studio or another local OpenAI-compatible model server. They produce structured transcripts, logs, patches, summaries, and artifacts into per-conversation folders. A local dashboard renders those artifacts as conversation-like task threads.

## Target Workflow

1. The user asks Codex for a feature, fix, review, or investigation.
2. Codex decides which parts can be delegated to local workers.
3. Codex or the user creates tasks in the Swarm Codex session for the current root conversation.
4. The swarm host starts one or more worker instances with scoped configs.
5. Workers write all output to durable run folders.
6. The local web dashboard displays agents, tasks, worker threads, logs, diffs, and status.
7. The user can inspect or join any worker conversation.
8. Codex reviews worker outputs and decides what to accept, reject, retry, or integrate.

## Architecture

```text
Codex Desktop Conversation
  Supervisor, planning, judgment, final integration

Swarm Host
  Local process manager and API server
  Maps Codex root conversations to swarm sessions
  Starts worker instances
  Captures stdout, structured events, logs, diffs, and artifacts

Worker Runtime Adapters
  Codex CLI/app-server in OSS/LM Studio mode
  opencode
  aider
  custom LM Studio worker

Run Store
  SQLite for queryable metadata
  JSONL and files for durable audit trails

Web Dashboard
  Localhost app loaded in Codex right-hand panel
  Shows conversation-local agents and task threads
```

## Key Design Principle

The swarm is subordinate to the parent Codex conversation. Local workers do not replace the supervisor. They perform bounded work and return evidence.

## Conversation Mapping

Each Codex root conversation gets one swarm session. When the Reasoning Framework is available, the natural key is the active `conversation_uuid`, not a display label or transient thread title.

```text
Codex root conversation_uuid
  Swarm session
    Agents
    Tasks
    Runs
    Artifacts
```

The conversation UUID is the minimum survival token for context compaction. It resolves to the durable conversation surface:

```text
C:\Project\ReasoningFramework\platform\conversations\<conversation_uuid>.sop
```

Swarm Codex should treat that surface as the parent continuity handle for goals, active scope, unresolved items, reentry packets, citations, and cross-thread lineage.

Tasks and runs are distinct:

- Task: The intent, such as "map the auth flow" or "draft a patch for the parser".
- Run: One attempt by one agent/model/runtime to complete a task.

This allows retries, comparisons, and multiple agents working the same task.

## Worker Isolation

Preferred isolation is per root conversation UUID, not per installation.

For Codex CLI workers:

```powershell
$env:CODEX_HOME="C:\Project\Pinky\.swarm\codex-homes\<root-id>"
codex app-server --listen ws://127.0.0.1:<port>
```

The `CODEX_HOME` directory keeps config, session state, logs, worktrees, and local history separate.

For local-model Codex workers, configure that home for OSS/LM Studio mode:

```toml
oss_provider = "lmstudio"
model_provider = "oss"
model = "local-model-id"
```

Exact model IDs and provider details should be verified against the installed Codex CLI version and the LM Studio server model list.

## Local Model Server

LM Studio is expected to expose an OpenAI-compatible API at:

```text
http://localhost:1234/v1
```

Workers should support either built-in LM Studio provider configuration or a custom OpenAI-compatible provider.

## Inspectability Requirements

Every worker run must produce a durable, inspectable record:

```text
Task prompt
Worker config
Model/provider
Repository path and commit SHA
Transcript
Tool calls
Commands run
Exit codes
Files read
Files written
Patch/diff
Summary
Risks/open questions
Supervisor review
Final disposition
```

Workers must not disappear when they finish. They become records in the conversation-local swarm dashboard.

## Proposed File Layout

```text
.swarm/
  swarm.db
  conversations/
    <conversation_uuid>/
      session.json
      agents.json
      tasks/
        task-001.json
      runs/
        run-001/
          run.json
          prompt.md
          transcript.jsonl
          terminal.log
          commands.log
          files-read.json
          artifacts/
            patch.diff
            summary.md
            risks.md
            review.md
```

## Normalized Event Model

The dashboard should not depend on one worker implementation. Each adapter converts worker output into normalized events:

```json
{
  "event_id": "evt_001",
  "run_id": "run_001",
  "timestamp": "2026-06-19T00:00:00Z",
  "type": "agent_message_delta",
  "payload": {
    "text": "I found the parser entry point."
  }
}
```

Candidate event types:

```text
run_started
run_completed
run_failed
agent_message_delta
agent_message_completed
tool_call_started
tool_call_completed
command_started
command_completed
file_read
file_changed
patch_proposed
summary_written
supervisor_review_written
status_changed
```

## Web Dashboard

The dashboard is a local web app, served by the swarm host:

```text
http://127.0.0.1:<port>/sessions/<codex-root-id>
```

The Codex right-hand panel can load this page.

Views:

```text
Session overview
Agent list
Task list
Run detail
Transcript
Tool/command log
Diff/artifacts
Supervisor review
```

Controls:

```text
Create task
Start run
Cancel run
Retry run
Join worker conversation
Request supervisor review
Accept/reject artifact
Archive task
```

## MVP Scope

The first MVP should avoid complex UI and focus on durable worker records.

1. File-backed run store under `.swarm/`.
2. CLI command to create a session.
3. CLI command to create a task.
4. CLI command to run one local worker.
5. Capture stdout/stderr to `terminal.log`.
6. Capture transcript/events to `transcript.jsonl`.
7. Store final summary and optional patch.
8. Minimal local web page that lists tasks and shows run logs/artifacts.

## MVP Commands

```powershell
swarm init --repo C:\Project\Pinky
swarm session create --conversation-uuid <uuid>
swarm task create --session <conversation_uuid> --file task.md
swarm run start --task task-001 --adapter codex-oss
swarm list --session <conversation_uuid>
swarm show run-001
swarm serve --port 8787
```

## Worker Contract

Input:

```text
Task file
Allowed repository path
Allowed files or write policy
Model/provider config
Timeout
Command policy
Output directory
```

Output:

```text
transcript.jsonl
terminal.log
commands.log
summary.md
risks.md
patch.diff, when applicable
status.json
```

## Safety Model

Local workers should start with limited authority:

```text
Read-heavy tasks first
Patch output preferred over direct edits
No destructive shell commands
One writer at a time per worktree
Supervisor review required before integration
```

For write-heavy work, use per-worker git worktrees or patch-only output.

## Open Questions

1. Which worker runtime should be first: Codex CLI app-server, opencode, aider, or a custom LM Studio worker?
2. Can Codex CLI OSS mode fully support the local LM Studio model behavior needed for tool use?
3. How should the outer Codex conversation expose or initialize its active `conversation_uuid` when running outside the Reasoning Framework workspace?
4. Should the first UI be plain server-rendered HTML or a React/Svelte app?
5. Should workers modify files directly, or only emit patches for supervisor review?
6. How should the user "join" a nested worker conversation: through the dashboard, terminal attach, or a message injected into the worker runtime?
7. What event fields are necessary to faithfully render Codex app-server output?

## Recommended First Prototype

Start with a swarm host that supports one adapter and one dashboard.

Recommended adapter order:

1. Codex CLI app-server in LM Studio/OSS mode, if verified locally.
2. opencode, if Codex CLI local-model behavior is insufficient.
3. custom LM Studio worker for narrow task types.

The first successful demo should show:

```text
Outer Codex creates a task
Local worker runs against LM Studio
Dashboard shows the worker transcript
Worker writes a patch or summary
Outer Codex reviews the artifact
```
