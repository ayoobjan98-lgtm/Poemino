from django.db.models import Q

from MakerPom.datejalali import jalali_to_gregorian


def filter_poems(poems, params):

    # ---------------------------------------------------------
    # General Search
    # ---------------------------------------------------------

    q = params.get("q", "").strip()

    if q:
        poems = poems.filter(
            Q(name__icontains=q)
            | Q(text__icontains=q)
            | Q(author__first_name__icontains=q)
            | Q(author__last_name__icontains=q)
        )

    # ---------------------------------------------------------
    # Author
    # ---------------------------------------------------------

    author = params.get("author", "").strip()

    if author:
        poems = poems.filter(
            Q(author__first_name__icontains=author)
            | Q(author__last_name__icontains=author)
        )

    # ---------------------------------------------------------
    # Title
    # ---------------------------------------------------------

    title = params.get("title", "").strip()

    if title:
        poems = poems.filter(
            name__icontains=title
        )

    # ---------------------------------------------------------
    # Poem Type
    # ---------------------------------------------------------

    poem_type = params.get("poem_type", "").strip()

    if poem_type:
        poems = poems.filter(
            poem_type=poem_type
        )

    # ---------------------------------------------------------
    # Poem Date
    # ---------------------------------------------------------

    poem_date = params.get("poem_date", "").strip()

    if poem_date:

        gregorian_date = jalali_to_gregorian(
            poem_date
        )

        if gregorian_date is None:
            return poems.none()

        poems = poems.filter(
            created_at__date=gregorian_date
        )

    return poems


