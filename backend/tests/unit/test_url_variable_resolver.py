"""Unit tests for url_variable_resolver.URLVariableResolver.

URLVariableResolver expands PHP-style {{date}}/{{time}} variables in job
url_templates (scheduled-scraping URL generation). It is pure (stdlib only) and
deterministic when given a fixed exec_time, so these tests pin every documented
behavior: format conversion, time offsets, timezone resolution, validation, and
the preview payload. It had no coverage before; utils.resolve_url_template and
validators.JobValidator both call into it on the live job-create/run path.
"""
from datetime import datetime, timezone

from url_variable_resolver import URLVariableResolver


# 2026-01-22 20:00:00 UTC -- matches the module docstring's worked examples
# ({{date:Y-m-d_h_iA}} -> 2026-01-22_08_00PM, {{time:H_i}} -> 20_00).
FIXED = datetime(2026, 1, 22, 20, 0, 0, tzinfo=timezone.utc)

# A single-digit-everything instant for no-leading-zero / 12h coverage:
# 2026-03-05 08:07:09 UTC (month 3, day 5, hour 8, minute 7, second 9).
SINGLE_DIGIT = datetime(2026, 3, 5, 8, 7, 9, tzinfo=timezone.utc)


class TestResolveBasic:
    def test_no_variables_returned_unchanged(self):
        url = "https://example.com/api/v1/static-path?q=1"
        assert URLVariableResolver.resolve(url, FIXED) == url

    def test_date_default_format(self):
        assert URLVariableResolver.resolve("{{date}}", FIXED) == "2026-01-22"

    def test_time_default_format(self):
        # default time format is H:i:s
        assert URLVariableResolver.resolve("{{time}}", FIXED) == "20:00:00"

    def test_date_with_slash_format(self):
        assert URLVariableResolver.resolve("{{date:m/d/Y}}", FIXED) == "01/22/2026"

    def test_docstring_compound_format(self):
        assert (
            URLVariableResolver.resolve("{{date:Y-m-d_h_iA}}", FIXED)
            == "2026-01-22_08_00PM"
        )

    def test_time_custom_format(self):
        assert URLVariableResolver.resolve("{{time:H_i}}", FIXED) == "20_00"

    def test_two_digit_year(self):
        assert URLVariableResolver.resolve("{{date:y}}", FIXED) == "26"

    def test_variable_embedded_in_url(self):
        out = URLVariableResolver.resolve(
            "https://api.example.com/reports/{{date:Y-m-d}}.json", FIXED
        )
        assert out == "https://api.example.com/reports/2026-01-22.json"

    def test_multiple_variables_in_one_template(self):
        out = URLVariableResolver.resolve(
            "https://x/{{date:Y-m-d}}/{{time:H_i}}", FIXED
        )
        assert out == "https://x/2026-01-22/20_00"

    def test_unknown_format_char_passes_through_as_literal(self):
        # 'Q' is not a PHP specifier, so it is emitted verbatim.
        assert URLVariableResolver.resolve("{{date:Q}}", FIXED) == "Q"


class TestResolveOffsets:
    def test_plus_one_day(self):
        assert URLVariableResolver.resolve("{{date+1d:Y-m-d}}", FIXED) == "2026-01-23"

    def test_minus_one_day(self):
        assert URLVariableResolver.resolve("{{date-1d:Y-m-d}}", FIXED) == "2026-01-21"

    def test_plus_hours(self):
        # 20:00 + 2h = 22:00
        assert URLVariableResolver.resolve("{{time+2h:H_i}}", FIXED) == "22_00"

    def test_minus_minutes(self):
        # 20:00 - 30m = 19:30
        assert URLVariableResolver.resolve("{{time-30m:H_i}}", FIXED) == "19_30"

    def test_plus_seconds(self):
        # 20:00:00 + 15s = 20:00:15
        assert URLVariableResolver.resolve("{{time+15s:H_i_s}}", FIXED) == "20_00_15"

    def test_offset_rolls_into_previous_day(self):
        # 2026-01-22 00:30 UTC minus 1h crosses midnight back to 2026-01-21.
        early = datetime(2026, 1, 22, 0, 30, 0, tzinfo=timezone.utc)
        assert URLVariableResolver.resolve("{{date-1h:Y-m-d}}", early) == "2026-01-21"

    def test_apply_offset_no_offset_returns_base(self):
        assert URLVariableResolver._apply_offset(FIXED, None) is FIXED

    def test_apply_offset_unrecognized_unit_falls_through_to_zero_delta(self):
        # resolve()'s regex never emits a non-dhms unit; this pins only the
        # deltas.get(unit, timedelta()) fallback for a numeric value with an
        # unrecognized trailing unit (the int() parse still succeeds here).
        assert URLVariableResolver._apply_offset(FIXED, "+5x") == FIXED


class TestNoLeadingZeroAndLowercase:
    def test_no_leading_zero_month_and_day(self):
        # n -> 3 (not 03), j -> 5 (not 05)
        assert URLVariableResolver.resolve("{{date:n/j}}", SINGLE_DIGIT) == "3/5"

    def test_padded_month_and_day(self):
        assert URLVariableResolver.resolve("{{date:m-d}}", SINGLE_DIGIT) == "03-05"

    def test_no_leading_zero_24h_hour(self):
        # G -> 8 (not 08), H -> 08
        assert URLVariableResolver.resolve("{{time:G}}", SINGLE_DIGIT) == "8"
        assert URLVariableResolver.resolve("{{time:H}}", SINGLE_DIGIT) == "08"

    def test_no_leading_zero_12h_hour(self):
        # g -> 8 (not 08), h -> 08
        assert URLVariableResolver.resolve("{{time:g}}", SINGLE_DIGIT) == "8"
        assert URLVariableResolver.resolve("{{time:h}}", SINGLE_DIGIT) == "08"

    def test_lowercase_meridiem(self):
        assert URLVariableResolver.resolve("{{time:a}}", SINGLE_DIGIT) == "am"

    def test_uppercase_meridiem(self):
        assert URLVariableResolver.resolve("{{time:A}}", FIXED) == "PM"


class TestTwelveHourWrap:
    def test_midnight_maps_to_twelve(self):
        midnight = datetime(2026, 1, 22, 0, 15, 0, tzinfo=timezone.utc)
        assert URLVariableResolver.resolve("{{time:h_iA}}", midnight) == "12_15AM"
        assert URLVariableResolver.resolve("{{time:g}}", midnight) == "12"

    def test_noon_maps_to_twelve_pm(self):
        noon = datetime(2026, 1, 22, 12, 0, 0, tzinfo=timezone.utc)
        assert URLVariableResolver.resolve("{{time:h_iA}}", noon) == "12_00PM"


class TestTimezone:
    def test_resolves_in_target_timezone_same_day(self):
        # 20:00 UTC is 15:00 in America/New_York (EST, UTC-5) on the same date.
        assert (
            URLVariableResolver.resolve("{{time:H_i}}", FIXED, tz="America/New_York")
            == "15_00"
        )
        assert (
            URLVariableResolver.resolve("{{date:Y-m-d}}", FIXED, tz="America/New_York")
            == "2026-01-22"
        )

    def test_timezone_can_roll_the_date_back(self):
        # 2026-01-22 02:00 UTC is 2026-01-21 21:00 in New York.
        early = datetime(2026, 1, 22, 2, 0, 0, tzinfo=timezone.utc)
        assert (
            URLVariableResolver.resolve("{{date:Y-m-d}}", early, tz="America/New_York")
            == "2026-01-21"
        )

    def test_invalid_timezone_falls_back_to_utc_without_raising(self):
        assert (
            URLVariableResolver.resolve("{{time:H_i}}", FIXED, tz="Not/AZone")
            == "20_00"
        )


class TestHasVariables:
    def test_true_when_template_has_variable(self):
        assert URLVariableResolver.has_variables("https://x/{{date}}") is True

    def test_false_for_static_template(self):
        assert URLVariableResolver.has_variables("https://x/static") is False

    def test_false_for_malformed_pseudo_variable(self):
        # {{bad}} is not a recognized variable, so it does not count.
        assert URLVariableResolver.has_variables("{{bad}}") is False


class TestExtractVariables:
    def test_extracts_plain_date(self):
        assert URLVariableResolver.extract_variables("{{date}}") == [
            {"type": "date", "offset": None, "format": None}
        ]

    def test_extracts_offset_and_format(self):
        assert URLVariableResolver.extract_variables("{{date+1d:Y-m-d}}") == [
            {"type": "date", "offset": "+1d", "format": "Y-m-d"}
        ]

    def test_extracts_multiple(self):
        assert URLVariableResolver.extract_variables(
            "{{date}}/{{time:H_i}}"
        ) == [
            {"type": "date", "offset": None, "format": None},
            {"type": "time", "offset": None, "format": "H_i"},
        ]

    def test_no_variables_returns_empty_list(self):
        assert URLVariableResolver.extract_variables("https://x/static") == []


class TestValidateTemplate:
    def test_empty_is_invalid(self):
        valid, error = URLVariableResolver.validate_template("")
        assert valid is False
        assert error == "Template cannot be empty"

    def test_unmatched_braces_invalid(self):
        valid, error = URLVariableResolver.validate_template("https://x/{{date}")
        assert valid is False
        assert error == "Unmatched braces in template"

    def test_plain_static_template_is_valid(self):
        assert URLVariableResolver.validate_template("https://x/static") == (True, None)

    def test_valid_date_variable(self):
        assert URLVariableResolver.validate_template("https://x/{{date}}") == (True, None)

    def test_valid_offset_and_format(self):
        assert URLVariableResolver.validate_template("{{date+1d:Y-m-d}}") == (True, None)

    def test_invalid_variable_name(self):
        valid, error = URLVariableResolver.validate_template("{{bad}}")
        assert valid is False
        assert error == "Invalid variable syntax: {{bad}}"

    def test_unknown_format_chars_are_allowed_as_literals(self):
        # validate_template intentionally permits non-specifier chars (treated as
        # literals at resolve time), so a format with 'Q' still validates.
        assert URLVariableResolver.validate_template("{{date:Q-Y}}") == (True, None)


class TestValidateTimezone:
    def test_empty_is_valid(self):
        assert URLVariableResolver.validate_timezone("") == (True, None)

    def test_none_is_valid(self):
        assert URLVariableResolver.validate_timezone(None) == (True, None)

    def test_known_timezone_is_valid(self):
        assert URLVariableResolver.validate_timezone("America/New_York") == (True, None)

    def test_unknown_timezone_is_invalid(self):
        valid, error = URLVariableResolver.validate_timezone("Mars/Phobos")
        assert valid is False
        assert error == "Invalid timezone: Mars/Phobos"


class TestCommonTimezones:
    def test_contains_utc(self):
        assert "UTC" in URLVariableResolver.get_common_timezones()

    def test_returns_defensive_copy(self):
        tzs = URLVariableResolver.get_common_timezones()
        tzs.append("Fake/Zone")
        assert "Fake/Zone" not in URLVariableResolver.get_common_timezones()


class TestPreview:
    def test_valid_template_payload(self):
        result = URLVariableResolver.preview("https://x/{{date:Y-m-d}}", FIXED)
        assert result["valid"] is True
        assert result["error"] is None
        assert result["template"] == "https://x/{{date:Y-m-d}}"
        assert result["resolved"] == "https://x/2026-01-22"
        assert result["variables"] == [
            {"type": "date", "offset": None, "format": "Y-m-d"}
        ]
        assert result["timezone"] == "UTC"
        assert result["resolved_at"] == FIXED.isoformat()

    def test_invalid_template_payload(self):
        result = URLVariableResolver.preview("{{bad}}", FIXED)
        assert result["valid"] is False
        assert result["error"] == "Invalid variable syntax: {{bad}}"
        assert result["resolved"] is None
        assert result["variables"] == []
        assert result["timezone"] == "UTC"

    def test_invalid_timezone_payload(self):
        result = URLVariableResolver.preview("{{date}}", FIXED, tz="Mars/Phobos")
        assert result["valid"] is False
        assert result["error"] == "Invalid timezone: Mars/Phobos"
        assert result["resolved"] is None
        assert result["timezone"] == "Mars/Phobos"

    def test_timezone_reflected_in_resolved_and_timestamp(self):
        result = URLVariableResolver.preview(
            "{{time:H_i}}", FIXED, tz="America/New_York"
        )
        assert result["valid"] is True
        assert result["resolved"] == "15_00"
        assert result["timezone"] == "America/New_York"
        # resolved_at carries the New-York-local wall clock (15:00), not UTC.
        assert result["resolved_at"].startswith("2026-01-22T15:00:00")
