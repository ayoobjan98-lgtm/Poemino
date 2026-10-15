# your_app_name/templatetags/jalali_filters.py

"""
Reusable Jalali (Persian) date/datetime utilities and Django template filters.

Features:
    - Gregorian -> Jalali
    - Jalali -> Gregorian
    - date / datetime support
    - timezone-aware datetime support
    - Persian / English digits
    - custom formatting
    - relative Persian time
    - usable directly from Python
    - usable inside Django templates

Dependencies:
    pip install jdatetime
"""

from __future__ import annotations

import datetime
import re
from typing import Any, Optional, Union

import jdatetime

from django import template
from django.utils import timezone


register = template.Library()


# ============================================================================
# CONSTANTS
# ============================================================================

EN_TO_FA = str.maketrans(
    "0123456789",
    "۰۱۲۳۴۵۶۷۸۹",
)

FA_TO_EN = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹",
    "0123456789",
)


GregorianValue = Union[
    datetime.date,
    datetime.datetime,
    str,
]

JalaliValue = Union[
    jdatetime.date,
    jdatetime.datetime,
    datetime.date,
    datetime.datetime,
    str,
]


# ============================================================================
# DIGITS
# ============================================================================

def to_persian_digits(value: Any) -> str:
    """
    Convert English digits to Persian digits.

    Example:
        to_persian_digits("1405/05/10")
        -> "۱۴۰۵/۰۵/۱۰"
    """

    if value is None:
        return ""

    return str(value).translate(EN_TO_FA)


def to_english_digits(value: Any) -> str:
    """
    Convert Persian digits to English digits.

    Example:
        to_english_digits("۱۴۰۵/۰۵/۱۰")
        -> "1405/05/10"
    """

    if value is None:
        return ""

    return str(value).translate(FA_TO_EN)


# ============================================================================
# TIMEZONE HELPERS
# ============================================================================

def _make_aware_if_needed(
    dt: datetime.datetime,
) -> datetime.datetime:
    """
    Make a datetime timezone-aware when necessary.
    """

    if timezone.is_naive(dt):
        return timezone.make_aware(
            dt,
            timezone.get_current_timezone(),
        )

    return dt


def _normalize_datetime(
    dt: datetime.datetime,
) -> datetime.datetime:
    """
    Normalize datetime for Django timezone handling.
    """

    try:
        dt = _make_aware_if_needed(dt)

        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)

        return dt

    except (
        ValueError,
        TypeError,
        OverflowError,
        AttributeError,
    ):
        return dt


# ============================================================================
# STRING PARSING
# ============================================================================

def _clean_date_string(value: str) -> str:
    """
    Normalize a date string before parsing.

    Supports Persian digits and common separators.
    """

    value = value.strip()

    # Persian digits -> English
    value = value.translate(FA_TO_EN)

    # Normalize common separators
    value = value.replace("-", "/")
    value = value.replace(".", "/")

    return value


def _parse_gregorian_string(
    value: str,
) -> Optional[Union[datetime.date, datetime.datetime]]:
    """
    Parse common Gregorian date/datetime strings.

    Supported examples:

        2026/08/24
        2026-08-24
        2026/08/24 21:30
        2026-08-24 21:30:45
        2026/08/24 21:30:45.123456
    """

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    normalized = _clean_date_string(value)

    # ISO-style datetime
    candidates = [
        normalized.replace("/", "-"),
        normalized,
    ]

    for candidate in candidates:
        try:
            return datetime.datetime.fromisoformat(candidate)
        except ValueError:
            pass

    # Date only
    date_patterns = [
        r"^(\d{4})/(\d{1,2})/(\d{1,2})$",
        r"^(\d{4})-(\d{1,2})-(\d{1,2})$",
    ]

    for pattern in date_patterns:
        match = re.match(pattern, normalized)

        if match:
            year, month, day = map(
                int,
                match.groups(),
            )

            try:
                return datetime.date(
                    year,
                    month,
                    day,
                )
            except ValueError:
                return None

    return None


def _parse_jalali_string(
    value: str,
) -> Optional[Union[jdatetime.date, jdatetime.datetime]]:
    """
    Parse common Jalali date/datetime strings.

    Supported examples:

        1405/06/02
        ۱۴۰۵/۰۶/۰۲
        1405/06/02 21:30
        1405/06/02 21:30:45
    """

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    normalized = _clean_date_string(value)

    # Datetime
    datetime_patterns = [
        (
            r"^(\d{4})/(\d{1,2})/(\d{1,2})"
            r"\s+(\d{1,2}):(\d{1,2})$"
        ),
        (
            r"^(\d{4})/(\d{1,2})/(\d{1,2})"
            r"\s+(\d{1,2}):(\d{1,2}):(\d{1,2})$"
        ),
    ]

    for pattern in datetime_patterns:
        match = re.match(pattern, normalized)

        if not match:
            continue

        parts = list(
            map(
                int,
                match.groups(),
            )
        )

        if len(parts) == 5:
            year, month, day, hour, minute = parts
            second = 0
        else:
            year, month, day, hour, minute, second = parts

        try:
            return jdatetime.datetime(
                year,
                month,
                day,
                hour,
                minute,
                second,
            )
        except (
            ValueError,
            TypeError,
        ):
            return None

    # Date only
    date_patterns = [
        r"^(\d{4})/(\d{1,2})/(\d{1,2})$",
        r"^(\d{4})-(\d{1,2})-(\d{1,2})$",
    ]

    for pattern in date_patterns:
        match = re.match(
            pattern,
            normalized,
        )

        if not match:
            continue

        year, month, day = map(
            int,
            match.groups(),
        )

        try:
            return jdatetime.date(
                year,
                month,
                day,
            )
        except (
            ValueError,
            TypeError,
        ):
            return None

    return None


# ============================================================================
# GREGORIAN -> JALALI
# ============================================================================

def gregorian_to_jalali(
    value: GregorianValue,
) -> Optional[Union[jdatetime.date, jdatetime.datetime]]:
    """
    Convert Gregorian date/datetime/string to jdatetime object.

    Example:

        gregorian_to_jalali(
            datetime.datetime(2026, 8, 24)
        )
    """

    if value is None:
        return None

    try:
        # String input
        if isinstance(value, str):
            value = _parse_gregorian_string(value)

            if value is None:
                return None

        # Datetime input
        if isinstance(value, datetime.datetime):
            value = _normalize_datetime(value)

            return jdatetime.datetime.fromgregorian(
                datetime=value,
            )

        # Date input
        if isinstance(value, datetime.date):
            return jdatetime.date.fromgregorian(
                date=value,
            )

    except (
        ValueError,
        TypeError,
        OverflowError,
        AttributeError,
    ):
        return None

    return None


# ============================================================================
# JALALI -> GREGORIAN
# ============================================================================

def jalali_to_gregorian(
    value: JalaliValue,
) -> Optional[Union[datetime.date, datetime.datetime]]:
    """
    Convert Jalali date/datetime/string to Gregorian date/datetime.

    Examples:

        jalali_to_gregorian("1405/06/02")

        jalali_to_gregorian("1405/06/02 21:30")
    """

    if value is None:
        return None

    try:
        # String input
        if isinstance(value, str):
            value = _parse_jalali_string(value)

            if value is None:
                return None

        # jdatetime datetime
        if isinstance(
            value,
            jdatetime.datetime,
        ):
            return value.togregorian()

        # jdatetime date
        if isinstance(
            value,
            jdatetime.date,
        ):
            return value.togregorian()

        # Python datetime interpreted as Jalali
        if isinstance(
            value,
            datetime.datetime,
        ):
            return jdatetime.datetime(
                value.year,
                value.month,
                value.day,
                value.hour,
                value.minute,
                value.second,
                value.microsecond,
            ).togregorian()

        # Python date interpreted as Jalali
        if isinstance(
            value,
            datetime.date,
        ):
            return jdatetime.date(
                value.year,
                value.month,
                value.day,
            ).togregorian()

    except (
        ValueError,
        TypeError,
        OverflowError,
        AttributeError,
    ):
        return None

    return None


# ============================================================================
# FORMAT JALALI
# ============================================================================

def format_jalali(
    value: GregorianValue,
    fmt: Optional[str] = None,
    persian_digits: bool = True,
) -> str:
    """
    Convert Gregorian date/datetime to formatted Jalali string.

    Examples:

        format_jalali(
            datetime.datetime.now()
        )

        format_jalali(
            datetime.datetime.now(),
            "%Y/%m/%d"
        )

        format_jalali(
            datetime.datetime.now(),
            "%Y/%m/%d %H:%M",
            persian_digits=False
        )
    """

    jdt = gregorian_to_jalali(value)

    if jdt is None:
        return ""

    try:
        if fmt is None:
            if isinstance(
                jdt,
                jdatetime.datetime,
            ):
                fmt = "%Y/%m/%d %H:%M"
            else:
                fmt = "%Y/%m/%d"

        result = jdt.strftime(fmt)

        if persian_digits:
            result = to_persian_digits(result)

        return result

    except (
        ValueError,
        TypeError,
        OverflowError,
        AttributeError,
    ):
        return ""


# ============================================================================
# FORMAT GREGORIAN
# ============================================================================

def format_gregorian(
    value: JalaliValue,
    fmt: Optional[str] = None,
    persian_digits: bool = False,
) -> str:
    """
    Convert Jalali date/datetime to formatted Gregorian string.

    Example:

        format_gregorian(
            "1405/06/02"
        )

        -> "2026/08/24"
    """

    gregorian = jalali_to_gregorian(value)

    if gregorian is None:
        return ""

    try:
        if fmt is None:
            if isinstance(
                gregorian,
                datetime.datetime,
            ):
                fmt = "%Y/%m/%d %H:%M"
            else:
                fmt = "%Y/%m/%d"

        result = gregorian.strftime(fmt)

        if persian_digits:
            result = to_persian_digits(result)

        return result

    except (
        ValueError,
        TypeError,
        OverflowError,
        AttributeError,
    ):
        return ""


# ============================================================================
# MAIN PYTHON FRIENDLY FUNCTION
# ============================================================================

def to_jalali(
    value: GregorianValue,
    fmt: Optional[str] = None,
    persian_digits: bool = True,
) -> str:
    """
    Main Python API.

    Example:

        to_jalali(user.created_at)

        to_jalali(
            user.created_at,
            "%Y/%m/%d"
        )

        to_jalali(
            user.created_at,
            "%Y/%m/%d",
            False
        )
    """

    return format_jalali(
        value=value,
        fmt=fmt,
        persian_digits=persian_digits,
    )


def to_gregorian(
    value: JalaliValue,
    fmt: Optional[str] = None,
    persian_digits: bool = False,
) -> str:
    """
    Main Python API for Jalali -> Gregorian.

    Example:

        to_gregorian("۱۴۰۵/۰۶/۰۲")

        -> "2026/08/24"
    """

    return format_gregorian(
        value=value,
        fmt=fmt,
        persian_digits=persian_digits,
    )


# ============================================================================
# RELATIVE TIME
# ============================================================================

def jalali_timesince(
    value: Any,
) -> str:
    """
    Return human-readable Persian relative time.

    Examples:

        چند لحظه پیش
        ۵ دقیقه پیش
        ۲ ساعت پیش
        ۳ روز پیش
        ۱ ماه پیش
        ۲ سال پیش
    """

    if value is None:
        return ""

    try:
        # Pure date -> midnight
        if (
            isinstance(value, datetime.date)
            and not isinstance(
                value,
                datetime.datetime,
            )
        ):
            value = datetime.datetime.combine(
                value,
                datetime.time.min,
            )

        # String -> Gregorian datetime
        if isinstance(value, str):
            value = _parse_gregorian_string(value)

            if value is None:
                return ""

        if not isinstance(
            value,
            datetime.datetime,
        ):
            return ""

        value = _normalize_datetime(value)

        now = timezone.localtime(
            timezone.now()
        )

        delta = now - value

        # Future
        if delta.total_seconds() < 0:
            return ""

        seconds = int(
            delta.total_seconds()
        )

        minutes = seconds // 60
        hours = minutes // 60
        days = hours // 24
        months = days // 30
        years = days // 365

        def fa(number: int) -> str:
            return to_persian_digits(
                str(number)
            )

        if seconds < 60:
            return "چند لحظه پیش"

        if minutes < 60:
            return f"{fa(minutes)} دقیقه پیش"

        if hours < 24:
            return f"{fa(hours)} ساعت پیش"

        if days < 30:
            return f"{fa(days)} روز پیش"

        if months < 12:
            return f"{fa(months)} ماه پیش"

        return f"{fa(years)} سال پیش"

    except (
        ValueError,
        TypeError,
        OverflowError,
        AttributeError,
    ):
        return ""


# ============================================================================
# DJANGO TEMPLATE FILTERS
# ============================================================================

@register.filter(name="to_jalali")
def to_jalali_filter(
    value: Any,
    arg: Optional[str] = None,
) -> str:
    """
    Django template filter.

    Examples:

        {{ obj.created_at|to_jalali }}

        {{ obj.created_at|to_jalali:"%Y/%m/%d" }}

        {{ obj.created_at|to_jalali:"%Y/%m/%d|persian" }}
    """

    if value is None:
        return ""

    fmt: Optional[str] = None
    persian_digits = True

    if arg:
        parts = [
            part.strip()
            for part in arg.split("|")
        ]

        for part in parts:
            if not part:
                continue

            if part.lower() == "persian":
                persian_digits = True

            elif part.lower() in {
                "english",
                "en",
                "latin",
            }:
                persian_digits = False

            else:
                fmt = part

    return format_jalali(
        value=value,
        fmt=fmt,
        persian_digits=persian_digits,
    )


@register.filter(name="to_gregorian")
def to_gregorian_filter(
    value: Any,
    arg: Optional[str] = None,
) -> str:
    """
    Django template filter for Jalali -> Gregorian.

    Examples:

        {{ jalali_date|to_gregorian }}

        {{ jalali_date|to_gregorian:"%Y-%m-%d" }}

        {{ jalali_date|to_gregorian:"%Y/%m/%d|persian" }}
    """

    if value is None:
        return ""

    fmt: Optional[str] = None
    persian_digits = False

    if arg:
        parts = [
            part.strip()
            for part in arg.split("|")
        ]

        for part in parts:
            if not part:
                continue

            if part.lower() == "persian":
                persian_digits = True

            elif part.lower() in {
                "english",
                "en",
                "latin",
            }:
                persian_digits = False

            else:
                fmt = part

    return format_gregorian(
        value=value,
        fmt=fmt,
        persian_digits=persian_digits,
    )


@register.filter(name="jalali_timesince")
def jalali_timesince_filter(
    value: Any,
) -> str:
    """
    Django template filter for relative Persian time.
    """

    return jalali_timesince(value)


@register.filter(name="fa_digits")
def fa_digits_filter(
    value: Any,
) -> str:
    """
    Convert English digits to Persian digits.
    """

    return to_persian_digits(value)


@register.filter(name="en_digits")
def en_digits_filter(
    value: Any,
) -> str:
    """
    Convert Persian digits to English digits.
    """

    return to_english_digits(value)