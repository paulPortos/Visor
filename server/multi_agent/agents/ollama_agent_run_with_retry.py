"""Backwards-compatible shim for the renamed LLM retry helper."""

from multi_agent.agents.llm_agent_run_with_retry import (
    _llm_error_is_transient as _ollama_error_is_transient,
    llm_agent_run_with_retry as ollama_agent_run_with_retry,
)

__all__ = ['ollama_agent_run_with_retry', '_ollama_error_is_transient']