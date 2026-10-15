from datetime import datetime

from django.db.models import Q, QuerySet

from MakerPom.models import CreatPom

from MakerPom.templatetags.jalali_tags import jalali_to_gregorian


class InvalidPoemDateError(Exception):
    """Raised when the user supplies an unparseable/invalid poem_date."""
    def __init__(self, raw_value):
        super().__init__(raw_value)
        self.raw_value = raw_value


def _resolve_choice_value(choices, raw):
    """
    Return the stored value for a user-supplied string.

    Accepts either the stored value (e.g. 'ghazal') or the
    human-readable label (e.g. 'Ghazal'). Always returns a plain str,
    never a gettext lazy proxy.
    """
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    for value, label in choices:
        if raw == value:
            return value
    lowered = raw.lower()
    for value, label in choices:
        if str(label).lower() == lowered:
            return value
    return raw


def build_poem_queryset(base_queryset: QuerySet, params: dict) -> QuerySet:
    """
    Apply search and filters to a poem queryset.
    """
    qs = base_queryset.select_related("author")

    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(author__username__icontains=q)
            | Q(name__icontains=q)
            | Q(text__icontains=q)
        )

    author = (params.get("author") or "").strip()
    if author:
        qs = qs.filter(author__username__iexact=author)

    title = (params.get("title") or "").strip()
    if title:
        qs = qs.filter(name__icontains=title)

    poem_type_raw = (params.get("poem_type") or "").strip()
    if poem_type_raw:
        poem_type = _resolve_choice_value(CreatPom.POEM_TYPES, poem_type_raw)
        qs = qs.filter(poem_type=poem_type)

    poem_date_raw = (params.get("poem_date") or "").strip()
    if poem_date_raw:
        target_date = _parse_date(poem_date_raw)
        if target_date is None:
            raise InvalidPoemDateError(poem_date_raw)
        qs = qs.filter(
            Q(created_at__date=target_date) | Q(edited_at__date=target_date)
        )

    status_raw = (params.get("status") or "").strip()
    if status_raw:
        status_values = [
            _resolve_choice_value(CreatPom.STATUS_CHOICES, s.strip())
            for s in status_raw.split(",")
            if s.strip()
        ]
        if status_values:
            qs = qs.filter(status__in=status_values)

    return qs


def _parse_date(value):
    """
    Convert a user-provided date string to a Gregorian date object.
    """
    if not value:
        return None

    value = value.strip()

    gregorian = jalali_to_gregorian(value)
    if gregorian is None:
        try:
            gregorian = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    if hasattr(gregorian, "date"):
        return gregorian.date()
    return gregorian

def _status_label(value):
    """
    Return the human-readable label for a stored status value, as a
    plain str. Never returns a gettext_lazy proxy.
    """
    mapping = dict(CreatPom.STATUS_CHOICES)
    label = mapping.get(value, value)
    return str(label)


def _poem_type_label(value):
    """
    Return the human-readable label for a stored poem_type value, as a
    plain str. Never returns a gettext_lazy proxy.
    """
    mapping = dict(CreatPom.POEM_TYPES)
    label = mapping.get(value, value)
    return str(label)


def get_filter_params(request):
    """
    Extract filter params from request.GET.

    Returns:
        (params_dict, active_chips_list)
    """
    keys = ["q", "author", "title", "poem_type", "poem_date", "status"]
    params = {key: request.GET.get(key, "") for key in keys}

    chips = []

    if params.get("q"):
        chips.append(("q", "Search: " + str(params["q"])))

    if params.get("author"):
        chips.append(("author", "Author: " + str(params["author"])))

    if params.get("title"):
        chips.append(("title", "Title: " + str(params["title"])))

    if params.get("poem_type"):
        type_display = _poem_type_label(params["poem_type"])
        chips.append(("poem_type", "Poem Type: " + type_display))

    if params.get("poem_date"):
        chips.append(("poem_date", "Poem Date: " + str(params["poem_date"])))

    if params.get("status"):
        status_values = [s.strip() for s in params["status"].split(",") if s.strip()]
        status_labels = [_status_label(v) for v in status_values]
        chips.append(("status", "Status: " + ", ".join(status_labels)))

    return params, chips
