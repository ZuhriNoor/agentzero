"""Memory actions: remember_fact."""
from . import Action
from agentzero.tools.memory_tool import LocalMemoryTool

# Singleton instance
_memory = LocalMemoryTool()


def register() -> dict:
    return {
        "remember_fact": Action(
            name="remember_fact",
            description="Save a significant fact about the user to long-term memory.",
            run=lambda **p: _memory.remember_fact(fact=p.get("fact")),
            permission="remember_fact",
            category="tool",
        ),
    }
