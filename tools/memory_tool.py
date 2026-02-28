"""
Memory tool for AgentZero.
Provides the ability to save facts directly to ChromaDB (LongTermMemory).
"""
from memory import LongTermMemory

class LocalMemoryTool:
    def __init__(self):
        self.ltm = LongTermMemory('data/vector_db')

    def remember_fact(self, fact: str) -> str:
        if not fact:
            return "No fact provided to remember."
        try:
            self.ltm.add(text=fact)
            return f"Successfully saved fact to long-term memory: {fact}"
        except Exception as e:
            return f"Failed to save to memory: {e}"
