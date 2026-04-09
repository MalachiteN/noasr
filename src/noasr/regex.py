"""Regex postprocessor for ordered replacement pipeline."""

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".noasr"
REGEX_FILENAME = "regex.json"


class RegexProcessorError(Exception):
    """Base exception for regex processing errors."""

    pass


class InvalidRegexError(RegexProcessorError):
    """Raised when a regex pattern is invalid."""

    pass


class RegexProcessor:
    """
    Ordered regex replacement processor.

    Loads replacement rules from ~/.noasr/regex.json and applies them
    in order (top to bottom as they appear in the JSON file).

    Each rule in regex.json is a mapping of pattern -> replacement.
    Patterns are compiled as regular expressions with full regex support.
    Replacement strings support:
    - Capture groups: $1, $2, etc.
    - Escape sequences: \\n (newline), \\t (tab), etc.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """
        Initialize the regex processor.

        Args:
            config_dir: Path to the config directory. Defaults to ~/.noasr
        """
        self._config_dir = config_dir or DEFAULT_CONFIG_DIR
        self._rules: list[tuple[re.Pattern[str], str]] = []

    @property
    def config_dir(self) -> Path:
        """Get the config directory path."""
        return self._config_dir

    @property
    def rules(self) -> list[tuple[re.Pattern[str], str]]:
        """Get the loaded replacement rules."""
        return self._rules

    def load_rules(self, registry: dict[str, str] | None = None) -> int:
        """
        Load regex rules from registry dict or from file.

        Rules are stored as a list of (pattern, replacement) tuples to
        preserve order, since JSON dict order is preserved in Python 3.7+.

        Args:
            registry: Optional dict of rules. If None, loads from regex.json file.

        Returns:
            Number of rules loaded

        Raises:
            InvalidRegexError: If a regex pattern is invalid
        """
        self._rules = []

        if registry is None:
            registry = self._load_registry_from_file()

        # Process rules in order - JSON dict preserves insertion order
        for pattern_str, replacement in registry.items():
            try:
                compiled = re.compile(pattern_str)
                self._rules.append((compiled, replacement))
            except re.error as e:
                raise InvalidRegexError(
                    f"Invalid regex pattern '{pattern_str}': {e}"
                ) from e

        return len(self._rules)

    def _load_registry_from_file(self) -> dict[str, str]:
        """Load regex registry from the JSON file."""
        regex_path = self._config_dir / REGEX_FILENAME

        if not regex_path.exists():
            return {}

        try:
            with regex_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(
                f"Warning: Could not load regex registry: {e}",
                file=sys.stderr,
            )
            return {}

    def apply(self, text: str) -> str:
        """
        Apply all replacement rules to the text in order.

        Each rule is applied to the result of the previous rule,
        allowing cascading transformations.

        Args:
            text: Input text to transform

        Returns:
            Transformed text after all rules have been applied
        """
        result = text

        for pattern, replacement in self._rules:
            result = pattern.sub(self._process_replacement(replacement), result)

        return result

    def _process_replacement(self, replacement: str) -> str:
        """
        Process a replacement string to handle escapes and capture groups.

        Converts:
        - $1, $2, etc. to \\1, \\2 for Python re.sub compatibility
        - \\n to actual newline character
        - \\t to actual tab character
        - \\r to actual carriage return character

        Args:
            replacement: Raw replacement string from JSON

        Returns:
            Processed replacement string with escapes and capture groups resolved
        """
        # Convert $N capture group references to \N for Python re.sub
        # Use a function to handle this safely
        processed = self._convert_dollar_refs(replacement)

        # Now handle escape sequences
        processed = processed.replace("\\n", "\n")
        processed = processed.replace("\\t", "\t")
        processed = processed.replace("\\r", "\r")

        return processed

    def _convert_dollar_refs(self, replacement: str) -> str:
        """
        Convert $N capture group references to \\N format.

        Handles $10, $11 etc. by checking if the digit after $ forms
        a valid group number. Also handles escaped $ (\\$) to produce literal $.

        Args:
            replacement: Replacement string with potential $N refs

        Returns:
            String with $N converted to \\N
        """
        result = []
        i = 0
        while i < len(replacement):
            if replacement[i] == "\\" and i + 1 < len(replacement):
                # Escaped character - keep as-is (but unescape \$ to $)
                if replacement[i + 1] == "$":
                    result.append("$")
                    i += 2
                else:
                    result.append(replacement[i])
                    result.append(replacement[i + 1])
                    i += 2
            elif replacement[i] == "$" and i + 1 < len(replacement):
                # Potential capture group reference
                digit = replacement[i + 1]
                if digit.isdigit():
                    # Convert $N to \\N for Python re.sub
                    result.append("\\")
                    result.append(digit)
                    i += 2
                else:
                    result.append(replacement[i])
                    i += 1
            else:
                result.append(replacement[i])
                i += 1
        return "".join(result)

    def iter_rules(self) -> Iterator[tuple[str, str]]:
        """
        Iterate over rules as (pattern_str, replacement) pairs.

        Yields:
            Tuples of (original_pattern_string, replacement_string)
        """
        for pattern, replacement in self._rules:
            yield (pattern.pattern, replacement)


def process_text(
    text: str,
    config_dir: Path | None = None,
    registry: dict[str, str] | None = None,
) -> str:
    """
    Process text through the regex replacement pipeline.

    This is a convenience function that creates a processor, loads rules,
    and applies them to the text in one call.

    Args:
        text: Input text to transform
        config_dir: Optional config directory path
        registry: Optional pre-loaded registry dict

    Returns:
        Transformed text after all replacements

    Raises:
        InvalidRegexError: If a regex pattern is invalid
    """
    processor = RegexProcessor(config_dir)
    processor.load_rules(registry)
    return processor.apply(text)


def load_rules_from_dict(
    registry: dict[str, str],
) -> list[tuple[re.Pattern[str], str]]:
    """
    Load and compile regex rules from a dictionary.

    Rules are returned as a list of (compiled_pattern, replacement) tuples
    to preserve order. This is useful for testing with predefined rules
    without needing a file.

    Args:
        registry: Dict of pattern -> replacement mappings

    Returns:
        List of (compiled_pattern, replacement) tuples in order

    Raises:
        InvalidRegexError: If a regex pattern is invalid
    """
    rules: list[tuple[re.Pattern[str], str]] = []

    for pattern_str, replacement in registry.items():
        try:
            compiled = re.compile(pattern_str)
            rules.append((compiled, replacement))
        except re.error as e:
            raise InvalidRegexError(
                f"Invalid regex pattern '{pattern_str}': {e}"
            ) from e

    return rules


def _convert_dollar_refs(replacement: str) -> str:
    """
    Convert $N capture group references to \\N format.

    Handles $10, $11 etc. by checking if the digit after $ forms
    a valid group number. Also handles escaped $ (\\$) to produce literal $.

    Args:
        replacement: Replacement string with potential $N refs

    Returns:
        String with $N converted to \\N
    """
    result = []
    i = 0
    while i < len(replacement):
        if replacement[i] == "\\" and i + 1 < len(replacement):
            # Escaped character - keep as-is (but unescape \$ to $)
            if replacement[i + 1] == "$":
                result.append("$")
                i += 2
            else:
                result.append(replacement[i])
                result.append(replacement[i + 1])
                i += 2
        elif replacement[i] == "$" and i + 1 < len(replacement):
            # Potential capture group reference
            digit = replacement[i + 1]
            if digit.isdigit():
                # Convert $N to \\N for Python re.sub
                result.append("\\")
                result.append(digit)
                i += 2
            else:
                result.append(replacement[i])
                i += 1
        else:
            result.append(replacement[i])
            i += 1
    return "".join(result)


def apply_rules(
    text: str,
    rules: list[tuple[re.Pattern[str], str]],
) -> str:
    """
    Apply a list of pre-compiled regex rules to text.

    Rules are applied in order, with each rule's output becoming
    the input for the next rule.

    Args:
        text: Input text to transform
        rules: List of (compiled_pattern, replacement) tuples

    Returns:
        Transformed text after all rules applied
    """
    result = text

    for pattern, replacement in rules:
        # Convert $N refs to \N and process escape sequences
        processed = _convert_dollar_refs(replacement)
        processed = processed.replace("\\n", "\n")
        processed = processed.replace("\\t", "\t")
        processed = processed.replace("\\r", "\r")
        result = pattern.sub(processed, result)

    return result
