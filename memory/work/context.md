# Work Context

## Project Overview
- **llm_senior**: An AI coworker agent system with persistent memory and daemon capabilities
- Repository location: `/home/liangwang/llm_senior`
- Version control: Sapling (`.hg`)

## System Architecture

### Core Components
- **Agent System** (`src/agent.py`): Main agent logic
- **Context Management** (`src/context.py`): Context handling and memory integration
- **Daemon** (`src/daemon.py`): Background process manager
- **LLM Interface** (`src/llm.py`): Language model integration
- **GChat Integration** (`src/gchat.py`): Google Chat connectivity (recently debugged)
- **Feedback Loop** (`src/feedback.py`): User feedback processing

### Memory System (`memory/`)
- **Work log**: `work_log.jsonl` - activity tracking
- **Message queues**: `inbox.jsonl`, `outbox.jsonl` - async communication
- **State files**: `daemon_state.json`, `daemon.pid`, `session_id`
- **Logs**: `activity.log`, `daemon.stdout.log`, `daemon.stderr.log`
- **Structured memory** (in progress): `people/`, `self/`, `work/` directories

### Scripts (`scripts/`)
- `start.py` - Daemon startup
- `onboard.py` - Initial setup/onboarding
- `calibrate.py` - Agent calibration
- `tell.py` - Send messages to agent
- `run_agent.py` - Direct agent execution
- `_daemon_entry.py` - Daemon entry point

## Recent Activity
- ✅ Fixed GChat integration bugs preventing daemon operation
- ✅ Initial repository setup completed
- 🔄 Memory structure being reorganized (new files in `memory/self/`, `memory/work/`, `memory/people/`)

## Current State
- **Modified files**: Core modules updated (agent, context, daemon, llm, work_log)
- **Missing files**: Legacy memory files being migrated (`current_work.md`, `lessons.md`, `team.md`, `src/scaffold.md`)
- **New structure**: Migrating to organized memory hierarchy (self-knowledge, work context, people profiles)

## Key Capabilities
- Persistent memory across sessions
- Daemon mode for background operation
- Google Chat integration for async communication
- Message inbox/outbox queue system
- Activity and work logging