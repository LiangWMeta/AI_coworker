VERDICT: NEEDS_REVISION

## Summary Assessment

The design captures an ambitious and compelling vision for an autonomous AI coworker, but it is significantly over-engineered for a v1 given the user's explicit emphasis on simplicity. The 25-file project structure, 4-engine architecture, and 25-step implementation plan contradict the "keep it simple" constraint and will likely stall before delivering any working prototype.

## Critical Issues (must fix)

### 1. Project structure is 5x too large for a v1

The plan specifies ~25 source files across 5 packages with nested sub-packages (`context/sources/` with 5 adapters, `work/actions/` with 4 action types, etc.). For a v1 that proves the concept, this should be closer to 5-7 files total. Most of the "sources" adapters (gchat.py, workplace.py, dashboards.py) are deferred to Phase 4 anyway, so why define them in the project structure now?

**Recommendation:** Flatten to a single package. Something like: `agent.py` (main loop), `context.py` (ingestion + memory), `work.py` (executor + task picker), `feedback.py` (collection + storage), `calibration.py` (session runner), and a `scaffold.yaml`. Add sub-packages only when a file exceeds ~300 lines.

### 2. Phase ordering has hidden dependencies and defers the hardest problem

Phase 1 builds the Context Engine (ingestion, understanding, memory) in isolation. But the Context Engine's value is only testable through the Work Engine (Phase 2) -- you cannot know if your "understanding" is correct until the agent tries to use it for real work. Meanwhile, the riskiest technical problem -- **making `claude -p` reliably execute multi-step work with injected context** -- is deferred to Phase 2, step 7.

**Recommendation:** Start with the Work Engine. Get `claude -p` executing a single, manually-specified task with manually-provided context (a hardcoded system prompt). Prove that the `claude -p` subprocess integration works, that tool access is reliable, and that permission boundaries hold. Then layer context ingestion on top of a working executor.

### 3. The `claude -p` integration design is underspecified and hides real complexity

The plan says "all LLM calls use `claude -p`" but does not address:
- **Context window management**: How do you fit team context + task context + memory into `claude -p`'s context window? What happens when it overflows? This is the #1 practical problem with this architecture.
- **Subprocess reliability**: `claude -p` is a subprocess call. What happens on timeouts, crashes, or malformed output? How do you parse structured responses from free-text pipe output?
- **Concurrent calls**: The Context Engine and Work Engine both need LLM calls. Can you run multiple `claude -p` processes? Is there rate limiting?
- **Session/conversation continuity**: Each `claude -p` call is stateless. How does the agent maintain working state across multiple calls within a single task?
- **Cost**: Continuous context re-synthesis + work execution + memory restructuring = a lot of LLM calls. Any estimate on token consumption?

**Recommendation:** Add a `llm.py` wrapper module that handles subprocess management, output parsing, error handling, and context window budgeting. This is the foundation everything else sits on -- design it explicitly.

### 4. Memory layer ("living structured knowledge base") is vaguely defined

The memory layer is described as "LLM-restructured understanding" that is "periodically re-synthesized" with the "LLM deciding when memory needs restructuring." This is hand-waving over a genuinely hard problem:
- What is the actual data format? Files on disk? A database? The plan lists `chromadb` as a dependency but never explains how it's used.
- How does the agent retrieve relevant context for a specific task? Full memory dump into the prompt? Vector search? Both?
- "LLM decides when memory needs restructuring" -- how? A meta-prompt? This creates a recursive problem.

**Recommendation:** For v1, use flat markdown files as the knowledge base (one per topic/project). Retrieve by filename/topic match, not vector search. Drop `chromadb` from v1 -- it adds operational complexity without proven value at this stage.

### 5. The Growth Engine (Phase 4) is premature abstraction

`scaffold_evolver.py`, `self_assessor.py`, and `learner.py` are three separate modules for what is, in v1, essentially: "after calibration, update the system prompt." This can be a single function, not three files with an entire "Growth Engine" abstraction.

**Recommendation:** Merge all of Phase 4's growth logic into the calibration module. After a calibration session produces ratings + feedback, a single function appends lessons learned to the scaffold YAML. That is the entire v1 growth loop.

### 6. Calibration system design ignores practical adoption barriers

The plan proposes weekly lightweight check-ins and quarterly deep calibrations with "multiple engineers." In practice:
- Engineers will not regularly use a custom CLI tool to rate an AI agent on 4 axes with 0-5 scores unless it takes under 2 minutes.
- The quarterly calibration with "multiple engineers" requires coordination overhead that will never happen for a v1 prototype.
- There is no description of how calibration results are actually consumed by the Growth Engine -- just that they exist.

**Recommendation:** For v1, calibration = one engineer runs a script that shows the agent's recent work log and answers 3-5 yes/no or thumbs-up/down questions. No multi-reviewer sessions. No 4-axis scoring. Store results in a JSON file. Prove the feedback loop works before building ceremony around it.

## Suggestions (nice to have)

### A. Start with a single "vertical slice" instead of horizontal layers

Instead of building Context Engine then Work Engine then Feedback then Growth sequentially, build one complete vertical: "Agent reads a task from a file, uses `claude -p` to investigate and propose a fix, human rates the result, scaffold gets updated." This proves the full loop in days, not weeks.

### B. Drop the L3-L7 seniority framework from v1

Five level-specific scaffold YAMLs are premature. The agent will start at "L3" and stay there for a while. Ship one scaffold, evolve it manually based on calibration, and formalize levels only after you have enough calibration data to distinguish between them.

### C. Simplify the permission model

The permission model (free vs. needs-approval) is well-conceived but can be implemented as a simple allowlist/blocklist in the scaffold prompt itself, not as a separate `permission.py` module. Example: "You may read files and run tests freely. Before running any command that modifies files, posts messages, or touches production, ask for approval."

### D. Add an explicit "demo day" milestone

The plan lacks a concrete "show this working" target. Define what the minimum demo looks like: e.g., "Agent reads 3 recent diffs from the repo, summarizes the team's current work, picks one open task, and proposes a solution." This focuses implementation on value delivery.

### E. Consider structured output from `claude -p`

Many calls to `claude -p` will need structured output (JSON task descriptions, structured feedback, etc.). The plan should specify how to get reliable structured output from pipe mode. Options: ask for JSON in the prompt and parse it, or use `claude -p` with `--output-format json` if available.

## Verified Claims (things you confirmed are correct)

1. **Core concept is sound.** An AI coworker that onboards, works, and gets calibrated like a human is a compelling framing that differentiates this from benchmark-driven approaches.

2. **`claude -p` as the LLM backend is a reasonable choice.** It avoids API key management, inherits tool access, and keeps the implementation in the CLI ecosystem. The tradeoffs (subprocess overhead, statelessness) are manageable.

3. **The permission model (free vs. needs-approval) is well-scoped.** The distinction between read/analyze (free) and write/deploy (needs approval) is the right boundary for an autonomous agent.

4. **The 4 dimensions (Impact, Judgment, Autonomy, Growth) are the right evaluation axes.** They map well to how real engineering performance is assessed.

5. **Continuous feedback from natural work outputs (diff reviews, task outcomes) is the right primary signal.** This is more scalable and authentic than structured rating sessions.

6. **The ingestion sources (chat, code, tasks, dashboards) are the right categories** for building team context, even if not all need to be implemented in v1.
