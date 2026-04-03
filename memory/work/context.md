# Work Context

## Project Overview
- **llm_senior**: AI coworker agent system with persistent memory and daemon capabilities
- Repository: `/home/liangwang/llm_senior`
- Version control: Sapling (`.hg/`) with legacy Git artifacts (`.git/`) present

## System Architecture

### Core Components
- **Agent System** (`src/agent.py`): Main agent logic
- **Context Management** (`src/context.py`): Context handling and memory integration
- **Daemon** (`src/daemon.py`): Background process manager
- **LLM Interface** (`src/llm.py`): Language model integration
- **GChat Integration** (`src/gchat.py`): Google Chat connectivity
- **Feedback Loop** (`src/feedback.py`): User feedback processing

### Memory System (`memory/`)

**Hierarchical structure:**
- `self/` - agent self-knowledge (7 files: lessons, level, mission, motivation, principles, rules, soul)
- `work/` - work context (context.md, focus.md)
- `people/` - people profiles (liangwang.md)

**Operational files:**
- `work_log.jsonl` - activity tracking
- `inbox.jsonl`, `outbox.jsonl` - async message queues
- `daemon_state.json`, `daemon.pid`, `session_id` - daemon state
- `activity.log`, `daemon.stdout.log`, `daemon.stderr.log` - logs
- `chat_history.jsonl` - conversation history

### Scripts (`scripts/`)
- `start.py` - daemon startup
- `_daemon_entry.py` - daemon entry point
- `run_agent.py` - direct agent execution
- `onboard.py` - initial setup
- `calibrate.py` - agent calibration
- `tell.py` - send messages to agent

### Supporting Files
- `tests/test_gchat_crash.py` - GChat integration tests
- `pyproject.toml` - project configuration
- `.gitignore` - version control exclusions
- `design-review-1.md` - design documentation

## Current State

### Recent Commits
1. Fix GChat integration bugs preventing daemon operation
2. Initial repository setup for llm-senior

### Working Copy Status

**Modified (pending commit):**
- `.gitignore`
- `src/agent.py`, `src/context.py`, `src/daemon.py`, `src/llm.py`
- `memory/work_log.jsonl`, `memory/outbox.jsonl`

**Removed (pending commit):**
- `memory/current_work.md`, `memory/lessons.md`, `memory/team.md`
- `src/scaffold.md`

**Untracked (ready to add):**
- `memory/self/` - 7 files (hierarchical self-knowledge structure)
- `memory/work/` - 2 files (context.md, focus.md)
- `memory/people/liangwang.md`
- `.git/` - legacy Git metadata artifacts

### Active Work
- Memory migration to hierarchical structure: **COMPLETED**
- Core modules updated to use new memory paths: **COMPLETED**
- GChat integration fixes: **COMPLETED**
- Next step: Commit changes (track new memory files, remove legacy files, update modified modules)

## Key Capabilities
- Persistent memory across sessions via hierarchical markdown structure
- Daemon mode for background operation
- Google Chat integration for async communication
- Message inbox/outbox queue system
- Activity and work logging
- Structured knowledge base (self-knowledge, work context, people profiles)