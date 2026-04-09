"""Tests for regex postprocessor functionality."""

import json
from pathlib import Path

import pytest

from noasr import regex


class TestRegexProcessorInit:
    """Test RegexProcessor initialization."""

    def test_default_config_dir(self) -> None:
        """Test that default config dir is ~/.noasr."""
        processor = regex.RegexProcessor()
        assert processor.config_dir == Path.home() / ".noasr"

    def test_custom_config_dir(self) -> None:
        """Test that custom config dir is accepted."""
        custom_dir = Path("/custom/path")
        processor = regex.RegexProcessor(config_dir=custom_dir)
        assert processor.config_dir == custom_dir


class TestLoadRules:
    """Test rule loading functionality."""

    def test_load_rules_from_dict(self) -> None:
        """Test loading rules from a dictionary."""
        processor = regex.RegexProcessor()
        registry = {
            r"hello": "world",
            r"foo": "bar",
        }

        count = processor.load_rules(registry)

        assert count == 2
        assert len(processor.rules) == 2
        # Verify order is preserved
        assert processor.rules[0][0].pattern == "hello"
        assert processor.rules[1][0].pattern == "foo"

    def test_load_rules_from_file(self, tmp_path: Path) -> None:
        """Test loading rules from a JSON file."""
        config_dir = tmp_path / ".noasr"
        config_dir.mkdir()
        regex_file = config_dir / "regex.json"
        regex_file.write_text(
            json.dumps(
                {
                    r"one": "1",
                    r"two": "2",
                }
            ),
            encoding="utf-8",
        )

        processor = regex.RegexProcessor(config_dir=config_dir)
        count = processor.load_rules()

        assert count == 2
        assert processor.rules[0][0].pattern == "one"
        assert processor.rules[1][0].pattern == "two"

    def test_load_rules_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Test that missing regex file results in empty rules."""
        config_dir = tmp_path / ".noasr"
        config_dir.mkdir()

        processor = regex.RegexProcessor(config_dir=config_dir)
        count = processor.load_rules()

        assert count == 0
        assert processor.rules == []

    def test_load_rules_invalid_json(self, tmp_path: Path) -> None:
        """Test that invalid JSON in regex file returns empty rules with warning."""
        config_dir = tmp_path / ".noasr"
        config_dir.mkdir()
        regex_file = config_dir / "regex.json"
        regex_file.write_text("not valid json", encoding="utf-8")

        processor = regex.RegexProcessor(config_dir=config_dir)
        count = processor.load_rules()

        assert count == 0

    def test_load_rules_invalid_regex_raises(self) -> None:
        """Test that invalid regex pattern raises InvalidRegexError."""
        processor = regex.RegexProcessor()
        registry = {
            r"[invalid": "replacement",  # Missing closing bracket
        }

        with pytest.raises(regex.InvalidRegexError) as exc_info:
            processor.load_rules(registry)

        assert "Invalid regex pattern" in str(exc_info.value)
        assert "[invalid" in str(exc_info.value)

    def test_load_rules_order_preserved(self) -> None:
        """Test that rule order is preserved from dict insertion order."""
        processor = regex.RegexProcessor()
        # Use OrderedDict-style ordering by inserting in specific order
        registry = {
            r"first": "1",
            r"second": "2",
            r"third": "3",
        }

        processor.load_rules(registry)

        assert processor.rules[0][0].pattern == "first"
        assert processor.rules[1][0].pattern == "second"
        assert processor.rules[2][0].pattern == "third"


class TestApply:
    """Test text transformation with apply()."""

    def test_apply_single_rule(self) -> None:
        """Test applying a single replacement rule."""
        processor = regex.RegexProcessor()
        processor.load_rules({r"hello": "world"})

        result = processor.apply("hello world")

        assert result == "world world"

    def test_apply_multiple_rules_order_matters(self) -> None:
        """Test that rule order affects output."""
        processor = regex.RegexProcessor()
        # Rule 1: replace "a" with "b"
        # Rule 2: replace "b" with "c"
        processor.load_rules(
            {
                r"a": "b",
                r"b": "c",
            }
        )

        result = processor.apply("a")

        # First rule turns "a" -> "b", then second rule turns "b" -> "c"
        assert result == "c"

    def test_apply_capture_groups(self) -> None:
        """Test that capture groups $1, $2 work in replacements."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"(\w+)-(\w+)": r"$2-$1",  # Swap hyphenated words
            }
        )

        result = processor.apply("hello-world")

        assert result == "world-hello"

    def test_apply_multiple_capture_groups(self) -> None:
        """Test multiple capture groups."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"(\d+)/(\d+)/(\d+)": r"$3-$1-$2",  # Rearrange date
            }
        )

        result = processor.apply("2024/04/10")

        assert result == "10-2024-04"

    def test_apply_escaped_newline(self) -> None:
        """Test that \n escape sequence produces actual newline."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r";": r"\n",
            }
        )

        result = processor.apply("hello;world")

        assert result == "hello\nworld"

    def test_apply_escaped_tab(self) -> None:
        """Test that \t escape sequence produces actual tab."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r",": r"\t",
            }
        )

        result = processor.apply("a,b")

        assert result == "a\tb"

    def test_apply_empty_text(self) -> None:
        """Test applying rules to empty text."""
        processor = regex.RegexProcessor()
        processor.load_rules({r"a": "b"})

        result = processor.apply("")

        assert result == ""

    def test_apply_no_rules(self) -> None:
        """Test applying no rules returns original text."""
        processor = regex.RegexProcessor()
        processor.load_rules({})

        result = processor.apply("unchanged text")

        assert result == "unchanged text"

    def test_apply_no_match(self) -> None:
        """Test that rules that don't match leave text unchanged."""
        processor = regex.RegexProcessor()
        processor.load_rules({r"xyz": "abc"})

        result = processor.apply("hello world")

        assert result == "hello world"


class TestProcessText:
    """Test the convenience function process_text()."""

    def test_process_text_with_registry(self) -> None:
        """Test process_text with inline registry."""
        result = regex.process_text(
            "hello",
            registry={r"hello": "world"},
        )

        assert result == "world"

    def test_process_text_preserves_order(self) -> None:
        """Test that process_text preserves rule order."""
        result = regex.process_text(
            "a",
            registry={
                r"a": "b",
                r"b": "c",
            },
        )

        assert result == "c"


class TestApplyRules:
    """Test the apply_rules helper function."""

    def test_apply_rules_with_compiled(self) -> None:
        """Test applying pre-compiled rules."""
        import re

        rules = [
            (re.compile(r"hello"), "hi"),
            (re.compile(r"world"), "earth"),
        ]

        result = regex.apply_rules("hello world", rules)

        assert result == "hi earth"


class TestIterRules:
    """Test the iter_rules method."""

    def test_iter_rules_returns_original_patterns(self) -> None:
        """Test that iter_rules yields original pattern strings."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"hello": "world",
                r"foo": "bar",
            }
        )

        rules_list = list(processor.iter_rules())

        assert len(rules_list) == 2
        assert rules_list[0] == (r"hello", "world")
        assert rules_list[1] == (r"foo", "bar")


class TestLoadRulesFromDict:
    """Test the load_rules_from_dict function."""

    def test_load_rules_from_dict_success(self) -> None:
        """Test loading rules from a simple dict."""
        registry = {
            r"a": "1",
            r"b": "2",
        }

        rules = regex.load_rules_from_dict(registry)

        assert len(rules) == 2
        assert rules[0][0].pattern == "a"
        assert rules[0][1] == "1"

    def test_load_rules_from_dict_invalid_regex(self) -> None:
        """Test that invalid regex raises InvalidRegexError."""
        registry = {
            r"(unclosed": "replacement",
        }

        with pytest.raises(regex.InvalidRegexError):
            regex.load_rules_from_dict(registry)


class TestInvalidRegexError:
    """Test InvalidRegexError exception."""

    def test_invalid_regex_error_message(self) -> None:
        """Test that error message contains the invalid pattern."""
        registry = {
            r"*invalid": "replacement",
        }

        with pytest.raises(regex.InvalidRegexError) as exc_info:
            regex.load_rules_from_dict(registry)

        assert "*invalid" in str(exc_info.value)

    def test_invalid_regex_error_is_base_exception(self) -> None:
        """Test that InvalidRegexError inherits from RegexProcessorError."""
        assert issubclass(regex.InvalidRegexError, regex.RegexProcessorError)


class TestCaptureGroupsAndEscapes:
    """Test capture groups and escape sequences together."""

    def test_capture_group_with_newline_escape(self) -> None:
        """Test capture group combined with newline escape."""
        processor = regex.RegexProcessor()
        # Replace "Name: X" with "X\n"
        processor.load_rules(
            {
                r"Name:\s*(\w+)": r"$1\n",
            }
        )

        result = processor.apply("Name: John")

        assert result == "John\n"

    def test_multiple_captures_with_spaces(self) -> None:
        """Test multiple capture groups with literal text."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"(\w+)\s+(\w+)": r"[$1][$2]",
            }
        )

        result = processor.apply("hello world")

        assert result == "[hello][world]"

    def test_dollar_sign_without_number(self) -> None:
        """Test that $ alone (not followed by digit) is preserved."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"price": r"$",
            }
        )

        result = processor.apply("price")

        assert result == "$"

    def test_double_dollar_escape(self) -> None:
        """Test that $$ produces a literal $."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"x": r"$$",
            }
        )

        result = processor.apply("x")

        assert result == "$$"


class TestEdgeCases:
    """Test edge cases."""

    def test_unicode_in_text(self) -> None:
        """Test that unicode text is handled correctly."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"hello": "你好",
            }
        )

        result = processor.apply("hello world")

        assert result == "你好 world"

    def test_unicode_in_pattern(self) -> None:
        """Test that unicode patterns work."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"你好": "hello",
            }
        )

        result = processor.apply("你好世界")

        assert result == "hello世界"

    def test_empty_pattern(self) -> None:
        """Test that empty pattern matches everywhere."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"": "X",  # This will insert X at every position
            }
        )

        result = processor.apply("ab")

        # Empty pattern matches at start, between chars, and at end
        assert "X" in result

    def test_complex_regex(self) -> None:
        """Test complex regex with word boundaries."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"\bword\b": "WORD",
            }
        )

        result = processor.apply("a word here")

        assert result == "a WORD here"

    def test_caret_anchor(self) -> None:
        """Test caret anchor matches start."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"^start": "BEGIN",
            }
        )

        result = processor.apply("start of something")

        assert result == "BEGIN of something"

    def test_dollar_anchor(self) -> None:
        """Test dollar anchor matches end."""
        processor = regex.RegexProcessor()
        processor.load_rules(
            {
                r"end$": "FINISH",
            }
        )

        result = processor.apply("something end")

        assert result == "something FINISH"
