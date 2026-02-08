"""
Example local file system tool for AgentZero.
"""
from . import Tool
import os

class LocalFileSystemTool(Tool):
    def __init__(self):
        super().__init__(
            name="filesystem",
            description="Access and manipulate local files and directories.",
            run=self.run_tool,
            permission="filesystem_access"
        )

    def run_tool(self, action: str, path: str, **kwargs):
        if action == "list":
            return os.listdir(path)
        elif action == "read":
            with open(path, 'r') as f:
                return f.read()
        elif action == "write":
            with open(path, 'w') as f:
                f.write(kwargs.get("content", ""))
                return True
        else:
            raise ValueError(f"Unknown action: {action}")
