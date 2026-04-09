"""Built-in tools for noasr."""

from datetime import datetime
from typing import Any

from noasr.tools import ITool, agenttool


@agenttool
class GetCurrentDateTime(ITool):
    """Tool to get current date and time."""

    @property
    def name(self) -> str:
        return "GetCurrentDateTime"

    @property
    def function(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Get the current date and time in the user's local timezone",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "description": "Optional datetime format string (default: ISO 8601)",
                            "enum": ["iso", "short", "full"],
                        }
                    },
                },
            },
        }

    def xeq(self, arguments: dict[str, Any]) -> str:
        """Execute the datetime tool.

        Args:
            arguments: May contain 'format' key with value 'iso', 'short', or 'full'.

        Returns:
            Current datetime as formatted string.
        """
        now = datetime.now()
        fmt = arguments.get("format", "iso")

        if fmt == "iso":
            return now.isoformat()
        elif fmt == "short":
            return now.strftime("%Y-%m-%d %H:%M")
        elif fmt == "full":
            return now.strftime("%A, %B %d, %Y at %I:%M %p")
        else:
            return now.isoformat()
