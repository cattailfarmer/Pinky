# Pinky SOP Awareness Node

`C:\Project\Pinky\.sop` is the active local SOP source authority root inside the
Pinky GitHub-facing repository.

It is meant to hold a thought-woven chain of SOP files, scan recent repository
changes between bookends, and emit inspectable SOP records about the correlations
that became sensitive during that span.

`F:\.sop` is the local backup and seed snapshot. Pinky publishes this `.sop`
authority through the Pinky repository remote, while the backup stays local unless
explicitly synchronized later.

## Verify

```powershell
python -m unittest discover runtime\tests
```

## Run A Sensitivity Scan

```powershell
python runtime\demos\sensitivity_scan.py --base-ref HEAD --head-ref WORKTREE
```

Emit the same scan as a SOP Hypergraph Record:

```powershell
python runtime\demos\sensitivity_scan.py --base-ref HEAD --head-ref WORKTREE --hypergraph
```

Render a focus/periphery attention frame:

```powershell
python runtime\demos\attention_frame.py "Narrative moment" --focus focus --periphery periphery narrative --correlates periphery:focus
```

Render a viewfinder snapshot:

```powershell
python runtime\demos\viewfinder_snapshot.py "Narrative token" --shape "desired attention shape" --previous-reflection old_frame --current-observation new_observation --reweigh narrative:2:5:"new observation"
```

Build a compiled attention kernel packet:

```powershell
python runtime\demos\attention_kernel.py --focus-subject "attention kernel runtime" --job-need "emit compact packet" --impulse "weave balance and impulse" --periphery-term balance --periphery-term impulse
```

Record a step-balance walk:

```powershell
python runtime\demos\step_balance_walk.py --focus-subject "continuous momentum in balance" --job-need "settle each step and name the next step" --impulse "walk the connected fabric" --step "read_state|Read focal state|stable|implement gait"
```

Record a periphery-continuity run:

```powershell
python runtime\demos\periphery_continuity_run.py --focus-subject "continuity periphery run" --direction forward --horizon "validation horizon" --impulse "run the path" --frame "frame_a|runtime continuity path opens|forward|balance,tests|repo_state,current_focus" --frame "frame_b|runtime continuity path validates|forward|balance,tests|repo_state,current_focus"
```

Prepare a Codex-master spool hub:

```powershell
python runtime\demos\spool_hub.py --turn-id spool_master_seed --objective "Coordinate worker lanes" --narrative-token "Codex as master over a visible worker spool"
```

For the first seed commit after it exists:

```powershell
python runtime\demos\sensitivity_scan.py --base-ref EMPTY_TREE --head-ref HEAD --output events\scans\seed_scan.sop
```

## Key Ideas

- A Git diff is a bookended event span.
- Changed SOP files are thought-current traces.
- Shared terms across changed files become correlation touches.
- Repeated touch and heat route subjects through surface, hair, skin, pressure,
  and impact sensitivity.
- SOP-HG (`.hg.sop`) is the hypergraph-shaped file profile for graphing
  bookends, events, changed files, signals, layers, and outside nodes.
- Attention frames add `N:focus:*`, `N:periphery:*`, and relation edges such as
  `E:correlates:*`, `E:causes:*`, `E:draws_attention:*`, and `E:digests:*`.
- Viewfinder snapshots add `N:viewfinder:*`, `N:snapshot:*`, `N:commit:*`,
  `N:reflection:*`, `N:observation:*`, and edges such as `E:projects:*`,
  `E:captures:*`, `E:compares:*`, `E:reweighs:*`, and `E:reframes:*`.
- Attention kernel packets compile ordered Security/Honesty preflight,
  boundary/identity/faculty-field surfaces, balance score, impulse, namespace
  checks, and reflection-consumption records into promptable context.
- Step-balance walks close each concrete action with balance score,
  settled state, correction move, next-step selection, and momentum effect.
- Periphery-continuity runs reduce checkpoint pressure when adjacent focus
  frames share stable rolling periphery and a coherent forward path.
- Spool hubs create a static `index.html` tree for turn-local LM Studio,
  Codex CLI, and manual worker lanes without launching them by default.
- Remote GitHub synchronization is performed through the Pinky repository, not
  through a nested `.sop` Git repository.
