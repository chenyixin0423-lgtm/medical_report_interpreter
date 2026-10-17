"""Compatibility import. New pipeline: interpreter.llm + interpreter.pipeline."""
from interpreter.llm import ClaudeGateway, ModelError

__all__ = ["ClaudeGateway", "ModelError"]
