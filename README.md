# AI Coworker

An autonomous AI teammate that onboards itself, works independently, and grows through real engineer feedback. Not a chatbot — a coworker.

## How It Works

The agent runs as a background daemon that:
- **Listens** to your GChat messages and responds
- **Watches** your code changes, task board, and chat activity
- **Acts** proactively when it detects something worth doing
- **Learns** by updating its own memory from every interaction
- **Grows** through calibration sessions where you rate its performance

## Quick Start

```bash
# 1. Onboard the agent to a repo
python3 scripts/onboard.py /path/to/your/repo

# 2. Start the daemon
python3 scripts/start.py /path/to/your/repo --owner <your-username>

# 3. Talk to it in the "AI Coworker" GChat space
#    Or via CLI:
python3 scripts/tell.py 'look into why the tests are failing'

# 4. Check its responses
python3 scripts/tell.py --read

# 5. See what it's been doing
python3 scripts/tell.py --log

# 6. Stop
python3 scripts/start.py stop
```

## Architecture

```
┌──────────────────────────────────┐
│         AI Coworker Agent        │
│                                  │
│  context.py ──→ agent.py ──→ feedback.py
│  (understand)   (work)      (learn)
│                                  │
│  daemon.py     gchat.py    llm.py
│  (always on)   (talk)    (claude -p)
└──────────────────────────────────┘
```

**LLM Backend**: `claude -p` (Claude Code pipe mode) — no API keys, inherits tool access.

## Memory System

The agent maintains structured memory that it actively reads and writes:

```
memory/
  self/                  # Who the agent is
    soul.md              # Core identity and values
    mission.md           # High-level purpose
    motivation.md        # What drives growth
    level.md             # Current seniority level (L3→L7)
    principles.md        # Decision-making framework
    rules.md             # Hard constraints and permissions
    lessons.md           # Accumulated wisdom from feedback
  people/                # Who the agent works with
    <username>.md        # Per-person profile, preferences, focus
  work/                  # What's happening now
    context.md           # Team, projects, codebase understanding
    focus.md             # Active priorities and tasks
```

All memory is managed by the LLM — it decides what to remember, what to update, and what to forget.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/start.py <repo>` | Start/stop/status the background daemon |
| `scripts/tell.py 'msg'` | Send a message to the agent |
| `scripts/tell.py --read` | Read agent notifications |
| `scripts/tell.py --log` | View activity log |
| `scripts/onboard.py <repo>` | Initial context ingestion |
| `scripts/calibrate.py <name>` | Run a calibration session |
| `scripts/run_agent.py 'task'` | One-shot task execution |

## Calibration

Rate the agent like a real engineer:

```bash
python3 scripts/calibrate.py yourname
```

Rates on 5 axes (1-5): Impact, Judgment, Autonomy, Quality, Growth. The agent's scaffold evolves based on feedback.

## Seniority Levels

| Level | Alias | Description |
|-------|-------|-------------|
| L3 | Junior | Executes defined tasks, asks about ambiguity |
| L4 | Mid | Breaks problems into sub-tasks, handles known patterns |
| L5 | Senior | Trade-off reasoning, pushes back, deep domain knowledge |
| L6 | Staff | Identifies unseen problems, designs strategies |
| L7 | Principal | Sets direction under uncertainty, challenges the mission |

Level emerges from human calibration, not synthetic benchmarks.

## Requirements

- Python 3.10+
- `claude` CLI (Claude Code)
- `gchat` CLI (for GChat integration, install via `devfeature install google_mux --persist`)
- No other dependencies
