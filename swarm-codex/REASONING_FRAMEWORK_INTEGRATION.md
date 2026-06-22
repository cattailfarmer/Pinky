# Reasoning Framework Integration

Swarm Codex should reuse the existing `C:\Project\ReasoningFramework` continuity model instead of inventing a separate long-term memory system.

## Existing Primitive

The Reasoning Framework defines `conversation_uuid` as the stable identity for one active conversation thread.

Key source:

```text
C:\Project\ReasoningFramework\platform\refinement\Conversation_Work_Attribution.sop
```

Important contract:

```text
conversation_uuid -> platform/conversations/{conversation_uuid}.sop
```

That UUID is the minimum survival token across compaction, restart, handoff, or reentry. The UUID alone should allow the system to reload the conversation surface and recover:

```text
reentry_packet
unresolved_items
active_scope
citation_index
handoff_warnings
workspace_scope
narrative references
```

## Swarm Mapping

Swarm Codex should map one parent `conversation_uuid` to one swarm session:

```text
Reasoning Framework conversation_uuid
  -> Swarm session
    -> Tasks
      -> Runs
        -> Worker transcripts and artifacts
```

Recommended local layout:

```text
C:\Project\Pinky\.swarm\conversations\<conversation_uuid>\
```

Recommended dashboard URL:

```text
http://127.0.0.1:8787/sessions/<conversation_uuid>
```

## Session Record

Each swarm session should include:

```json
{
  "conversation_uuid": "uuid",
  "conversation_surface": "C:/Project/ReasoningFramework/platform/conversations/uuid.sop",
  "repo_root": "C:/Project/Pinky",
  "created_at": "timestamp",
  "status": "active"
}
```

## Worker Run Record

Each run should retain parent lineage:

```json
{
  "run_id": "run-001",
  "task_id": "task-001",
  "parent_conversation_uuid": "uuid",
  "worker_conversation_uuid": "uuid-or-null",
  "adapter": "codex-oss",
  "model_provider": "lmstudio",
  "status": "running"
}
```

Worker conversations may also get their own UUIDs if they need durable identity beyond a single run. In that case, record a cross-thread lineage edge from the worker UUID to the parent UUID.

## Required Lifecycle

1. Resolve or create the parent `conversation_uuid`.
2. Ensure the parent conversation surface exists.
3. Create or load `.swarm/conversations/<conversation_uuid>/session.json`.
4. Load the parent reentry packet before planning delegated work.
5. Create tasks with the parent UUID embedded.
6. Start worker runs with an output directory under the parent session.
7. Append worker events and artifacts to the run folder.
8. Update the parent conversation surface after meaningful changes:
   - new task
   - run completed
   - patch proposed
   - user joined worker conversation
   - supervisor accepted or rejected output
   - unresolved item changed
   - reentry packet changed

## Compaction Survival

The outer conversation should keep this minimum token visible:

```text
active_conversation_uuid = <uuid>
```

After compaction or reentry, the recovery action is:

```text
load C:\Project\ReasoningFramework\platform\conversations\<uuid>.sop
load C:\Project\Pinky\.swarm\conversations\<uuid>\session.json
```

## Authority Boundary

Swarm output is evidence, not authority.

Worker transcripts, summaries, patches, and dashboards are carrier context. Codex or the user must review and accept them before they become implementation authority or project narrative authority.

## Implementation Implication

The first implementation task is not a worker adapter. It is the session substrate:

```text
conversation UUID resolution
session folder creation
session.json
task/run record schema
append-only transcript/event records
dashboard page keyed by conversation_uuid
```

