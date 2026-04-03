"""Wrapper for claude -p (Claude Code pipe mode)."""

import json
import subprocess
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Rough token budget — leave room for response in claude's context window
MAX_CONTEXT_CHARS = 100_000  # ~25k tokens, conservative


@dataclass
class LLMResult:
    text: str
    json_data: dict | None = None
    success: bool = True
    error: str | None = None


def run(
    prompt: str,
    system_prompt: str | None = None,
    output_format: str | None = None,
    model: str | None = None,
    timeout: int = 300,
    allowed_tools: str | None = None,
    session_id: str | None = None,
) -> LLMResult:
    """Call claude -p and return the result.

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system prompt (scaffold).
        output_format: "json" or "text" (default: text).
        model: Model override (e.g., "sonnet", "opus").
        timeout: Timeout in seconds (default: 5 minutes).
        allowed_tools: Tools to allow (e.g., "Bash,Read,Grep").
        session_id: Persistent session ID for conversation continuity.
    """
    cmd = ["claude", "-p"]

    if session_id:
        cmd.extend(["--session-id", session_id])
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    if output_format:
        cmd.extend(["--output-format", output_format])
    if model:
        cmd.extend(["--model", model])
    if allowed_tools:
        cmd.extend(["--allowedTools", allowed_tools])

    # Budget context: truncate prompt if too long
    if len(prompt) > MAX_CONTEXT_CHARS:
        logger.warning(
            f"Prompt too long ({len(prompt)} chars), truncating to {MAX_CONTEXT_CHARS}"
        )
        prompt = prompt[:MAX_CONTEXT_CHARS] + "\n\n[... truncated due to length ...]"

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return LLMResult(text="", success=False, error=f"claude -p timed out after {timeout}s")
    except FileNotFoundError:
        return LLMResult(text="", success=False, error="claude CLI not found in PATH")

    text = result.stdout.strip()

    if result.returncode != 0:
        # Filter out launcher noise from stderr — only keep real errors
        stderr_lines = [
            line for line in result.stderr.strip().splitlines()
            if not line.startswith(("E0", "Caller stack", "    /", "See S", "Meta Launcher",
                                    "Claude Code at Meta", "'Latest'", "Resolved", "Using"))
        ]
        stderr = "\n".join(stderr_lines).strip()
        return LLMResult(
            text=text,
            success=False,
            error=f"claude -p exited with code {result.returncode}: {stderr or '(see stdout)'}",
        )

    # Parse JSON if requested
    json_data = None
    if output_format == "json":
        try:
            json_data = json.loads(text)
            # Extract the actual response text from the JSON structure
            if isinstance(json_data, dict) and "result" in json_data:
                text = json_data["result"]
        except json.JSONDecodeError:
            logger.warning("Requested JSON output but got non-JSON response")

    return LLMResult(text=text, json_data=json_data, success=True)


def understand(content: str, instruction: str, model: str = "sonnet") -> str:
    """Use LLM to understand/synthesize content. Returns synthesized text.

    This is the key function that makes the Context Engine "smart" —
    it doesn't just store data, it calls the LLM to understand it.
    """
    prompt = f"""## Instruction
{instruction}

## Content to Analyze
{content}"""

    result = run(prompt, model=model)
    if not result.success:
        logger.error(f"LLM understanding failed: {result.error}")
        return f"[Error: {result.error}]"
    return result.text


def restructure_memory(current_memory: str, new_info: str, model: str = "sonnet") -> str:
    """Use LLM to restructure/update memory given new information.

    The LLM decides what to keep, update, or remove from the existing memory,
    and integrates the new information.
    """
    prompt = f"""You are maintaining a structured knowledge base for an AI coworker agent.

## Current Memory
{current_memory}

## New Information
{new_info}

## Task
Update the memory to integrate the new information. Rules:
- Keep the memory well-organized with clear markdown headers
- Remove outdated information that the new info supersedes
- Preserve important context that is still relevant
- Keep it concise — this memory will be injected into future prompts
- Use bullet points for facts, not prose

Output the complete updated memory document (not just the changes)."""

    result = run(prompt, model=model)
    if not result.success:
        logger.error(f"Memory restructuring failed: {result.error}")
        return current_memory  # Fall back to unchanged memory
    return result.text
