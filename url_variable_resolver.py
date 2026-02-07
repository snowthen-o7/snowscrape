"""
URL Variable Resolver - Supports PHP-style date formats for dynamic URL templates.

Supports variables like:
- {{date}} -> 2026-01-22 (default Y-m-d format)
- {{date:Y-m-d}} -> 2026-01-22
- {{date:m/d/Y}} -> 01/22/2026
- {{date:Y-m-d_h_iA}} -> 2026-01-22_08_00PM
- {{date+1d:Y-m-d}} -> tomorrow's date
- {{date-1d:Y-m-d}} -> yesterday's date
- {{time:H_i}} -> 20_00

Timezone support:
- Jobs can specify a timezone (e.g., 'America/New_York')
- Variables are resolved in that timezone at execution time
"""
import re
import platform
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo


class URLVariableResolver:
    """Resolves PHP-style date/time variables in URL templates."""

    # Pattern: {{date}}, {{date:format}}, {{date+1d}}, {{date-1d:format}}, {{time}}, etc.
    VARIABLE_PATTERN = re.compile(r'\{\{(date|time)([+-]\d+[dhms])?(:[^}]+)?\}\}')

    # Common timezones for UI dropdown
    COMMON_TIMEZONES = [
        'UTC',
        # US
        'America/New_York',      # Eastern
        'America/Chicago',       # Central
        'America/Denver',        # Mountain
        'America/Los_Angeles',   # Pacific
        'America/Anchorage',     # Alaska
        'Pacific/Honolulu',      # Hawaii
        # Europe
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'Europe/Rome',
        'Europe/Madrid',
        'Europe/Amsterdam',
        # Asia
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Asia/Hong_Kong',
        'Asia/Singapore',
        'Asia/Seoul',
        'Asia/Dubai',
        'Asia/Kolkata',
        # Australia
        'Australia/Sydney',
        'Australia/Melbourne',
        'Australia/Perth',
        # Other
        'Pacific/Auckland',
        'America/Toronto',
        'America/Vancouver',
        'America/Mexico_City',
        'America/Sao_Paulo',
    ]

    # PHP to Python strftime conversion
    # Note: %-m, %-d, %-H, %-I don't work on Windows, we handle this separately
    PHP_TO_PYTHON = {
        'Y': '%Y',  # 4-digit year (2026)
        'y': '%y',  # 2-digit year (26)
        'm': '%m',  # Month 01-12
        'n': '%m',  # Month 1-12 (no leading zero) - handled in post-processing
        'd': '%d',  # Day 01-31
        'j': '%d',  # Day 1-31 (no leading zero) - handled in post-processing
        'H': '%H',  # Hour 00-23
        'G': '%H',  # Hour 0-23 (no leading zero) - handled in post-processing
        'h': '%I',  # Hour 01-12
        'g': '%I',  # Hour 1-12 (no leading zero) - handled in post-processing
        'i': '%M',  # Minutes 00-59
        's': '%S',  # Seconds 00-59
        'A': '%p',  # AM/PM
        'a': '%p',  # am/pm (lowercase) - handled in post-processing
    }

    # Characters that need post-processing to remove leading zeros
    NO_LEADING_ZERO_CHARS = {'n', 'j', 'G', 'g'}

    # Characters that need lowercase conversion
    LOWERCASE_CHARS = {'a'}

    @classmethod
    def resolve(cls, template: str, exec_time: Optional[datetime] = None, tz: Optional[str] = None) -> str:
        """
        Resolve all variables in a URL template.

        Args:
            template: URL template containing {{date}} or {{time}} variables
            exec_time: The datetime to use for resolution (defaults to current time)
            tz: Timezone name (e.g., 'America/New_York'). If None, uses UTC.

        Returns:
            The resolved URL with all variables replaced
        """
        if exec_time is None:
            exec_time = datetime.now(timezone.utc)

        # Convert to target timezone if specified
        if tz:
            try:
                target_tz = ZoneInfo(tz)
                exec_time = exec_time.astimezone(target_tz)
            except Exception:
                # If timezone is invalid, fall back to UTC
                pass

        def replacer(match):
            var_type = match.group(1)       # 'date' or 'time'
            offset = match.group(2)          # '+1d', '-2h', etc. or None
            fmt = match.group(3)             # ':Y-m-d' (includes colon) or None

            # Apply time offset if specified
            target = cls._apply_offset(exec_time, offset)

            # Get format string (remove leading colon if present)
            php_format = fmt[1:] if fmt else ('Y-m-d' if var_type == 'date' else 'H:i:s')

            # Convert and format
            return cls._format_datetime(target, php_format)

        return cls.VARIABLE_PATTERN.sub(replacer, template)

    @classmethod
    def _apply_offset(cls, base: datetime, offset: Optional[str]) -> datetime:
        """
        Apply a time offset to a datetime.

        Args:
            base: The base datetime
            offset: Offset string like '+1d', '-2h', '+30m', '-15s'

        Returns:
            The adjusted datetime
        """
        if not offset:
            return base

        sign = 1 if offset[0] == '+' else -1
        value = int(offset[1:-1])
        unit = offset[-1]

        deltas = {
            'd': timedelta(days=sign * value),
            'h': timedelta(hours=sign * value),
            'm': timedelta(minutes=sign * value),
            's': timedelta(seconds=sign * value)
        }

        return base + deltas.get(unit, timedelta())

    @classmethod
    def _format_datetime(cls, dt: datetime, php_format: str) -> str:
        """
        Format a datetime using PHP-style format string.

        Args:
            dt: The datetime to format
            php_format: PHP-style format string (e.g., 'Y-m-d')

        Returns:
            Formatted datetime string
        """
        # Track which characters need post-processing
        no_zero_positions = []
        lowercase_positions = []

        # Convert PHP format to Python strftime format
        py_format = ''
        i = 0
        for char in php_format:
            if char in cls.PHP_TO_PYTHON:
                py_code = cls.PHP_TO_PYTHON[char]

                # Track positions that need post-processing
                if char in cls.NO_LEADING_ZERO_CHARS:
                    no_zero_positions.append(len(py_format))
                if char in cls.LOWERCASE_CHARS:
                    lowercase_positions.append(len(py_format))

                py_format += py_code
            else:
                # Keep non-format characters as-is
                py_format += char

        # Format the datetime
        result = dt.strftime(py_format)

        # Post-process: We need to handle this character-by-character
        # since strftime already ran. We'll rebuild with no leading zeros where needed.
        if no_zero_positions or lowercase_positions:
            result = cls._post_process_format(dt, php_format)

        return result

    @classmethod
    def _post_process_format(cls, dt: datetime, php_format: str) -> str:
        """
        Process format string character by character for proper handling
        of no-leading-zero formats and lowercase am/pm.
        """
        result = ''

        for char in php_format:
            if char == 'Y':
                result += str(dt.year)
            elif char == 'y':
                result += str(dt.year)[-2:]
            elif char == 'm':
                result += f'{dt.month:02d}'
            elif char == 'n':
                result += str(dt.month)
            elif char == 'd':
                result += f'{dt.day:02d}'
            elif char == 'j':
                result += str(dt.day)
            elif char == 'H':
                result += f'{dt.hour:02d}'
            elif char == 'G':
                result += str(dt.hour)
            elif char == 'h':
                hour12 = dt.hour % 12
                if hour12 == 0:
                    hour12 = 12
                result += f'{hour12:02d}'
            elif char == 'g':
                hour12 = dt.hour % 12
                if hour12 == 0:
                    hour12 = 12
                result += str(hour12)
            elif char == 'i':
                result += f'{dt.minute:02d}'
            elif char == 's':
                result += f'{dt.second:02d}'
            elif char == 'A':
                result += 'PM' if dt.hour >= 12 else 'AM'
            elif char == 'a':
                result += 'pm' if dt.hour >= 12 else 'am'
            else:
                # Keep non-format characters as-is
                result += char

        return result

    @classmethod
    def has_variables(cls, template: str) -> bool:
        """
        Check if a URL template contains any variables.

        Args:
            template: URL template to check

        Returns:
            True if template contains variables, False otherwise
        """
        return bool(cls.VARIABLE_PATTERN.search(template))

    @classmethod
    def extract_variables(cls, template: str) -> list:
        """
        Extract all variables from a URL template.

        Args:
            template: URL template to extract variables from

        Returns:
            List of tuples: (full_match, var_type, offset, format)
        """
        matches = cls.VARIABLE_PATTERN.findall(template)
        return [
            {
                'type': m[0],
                'offset': m[1] if m[1] else None,
                'format': m[2][1:] if m[2] else None  # Remove leading colon
            }
            for m in matches
        ]

    @classmethod
    def validate_template(cls, template: str) -> tuple:
        """
        Validate a URL template.

        Args:
            template: URL template to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str or None)
        """
        if not template:
            return False, "Template cannot be empty"

        # Check for unmatched braces
        open_braces = template.count('{{')
        close_braces = template.count('}}')
        if open_braces != close_braces:
            return False, "Unmatched braces in template"

        # Find all potential variables (including malformed ones)
        potential_vars = re.findall(r'\{\{([^}]*)\}\}', template)

        for var in potential_vars:
            # Parse the variable
            match = re.match(r'^(date|time)([+-]\d+[dhms])?(:.+)?$', var)
            if not match:
                return False, f"Invalid variable syntax: {{{{{var}}}}}"

            var_type, offset, fmt = match.groups()

            # Validate offset if present
            if offset:
                offset_match = re.match(r'^[+-]\d+[dhms]$', offset)
                if not offset_match:
                    return False, f"Invalid offset: {offset}"

            # Validate format if present
            if fmt:
                fmt_str = fmt[1:]  # Remove leading colon
                invalid_chars = set(fmt_str) - set(cls.PHP_TO_PYTHON.keys()) - set('_-/.: ')
                if invalid_chars:
                    # Allow literal characters that aren't format specifiers
                    pass

        return True, None

    @classmethod
    def validate_timezone(cls, tz: str) -> tuple:
        """
        Validate a timezone string.

        Args:
            tz: Timezone name to validate (e.g., 'America/New_York')

        Returns:
            Tuple of (is_valid: bool, error_message: str or None)
        """
        if not tz:
            return True, None  # Empty/None is valid (defaults to UTC)

        try:
            ZoneInfo(tz)
            return True, None
        except Exception as e:
            return False, f"Invalid timezone: {tz}"

    @classmethod
    def get_common_timezones(cls) -> list:
        """
        Get list of common timezones for UI dropdown.

        Returns:
            List of timezone strings
        """
        return cls.COMMON_TIMEZONES.copy()

    @classmethod
    def preview(cls, template: str, exec_time: Optional[datetime] = None, tz: Optional[str] = None) -> dict:
        """
        Generate a preview of the resolved URL and extracted variables.

        Args:
            template: URL template to preview
            exec_time: The datetime to use for resolution
            tz: Timezone name (e.g., 'America/New_York'). If None, uses UTC.

        Returns:
            Dictionary with resolved URL and variable information
        """
        if exec_time is None:
            exec_time = datetime.now(timezone.utc)

        is_valid, error = cls.validate_template(template)

        if not is_valid:
            return {
                'valid': False,
                'error': error,
                'template': template,
                'resolved': None,
                'variables': [],
                'timezone': tz or 'UTC'
            }

        # Validate timezone if provided
        if tz:
            tz_valid, tz_error = cls.validate_timezone(tz)
            if not tz_valid:
                return {
                    'valid': False,
                    'error': tz_error,
                    'template': template,
                    'resolved': None,
                    'variables': [],
                    'timezone': tz
                }

        resolved = cls.resolve(template, exec_time, tz)
        variables = cls.extract_variables(template)

        # Get the display time in the target timezone
        display_time = exec_time
        if tz:
            try:
                display_time = exec_time.astimezone(ZoneInfo(tz))
            except Exception:
                pass

        return {
            'valid': True,
            'error': None,
            'template': template,
            'resolved': resolved,
            'variables': variables,
            'timezone': tz or 'UTC',
            'resolved_at': display_time.isoformat()
        }
