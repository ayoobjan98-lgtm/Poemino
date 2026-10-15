from MakerPom.models import CreatPom


def dashboard_context(request):
    """
    Expose global dashboard context to every template:
      - pending_poem_count: how many poems are awaiting review
      - POEM_TYPES: the poem type choices from the model
      - POEM_STATUS_CHOICES: the status choices from the model
    """
    context = {
        'POEM_TYPES': CreatPom.POEM_TYPES,
        'POEM_STATUS_CHOICES': CreatPom.STATUS_CHOICES,
        'pending_poem_count': 0,
    }

    user = getattr(request, 'user', None)
    if user and user.is_authenticated and getattr(user, 'is_page_permitted', False):
        context['pending_poem_count'] = CreatPom.objects.select_related("author").filter(
            status=CreatPom.AWAITING_APPROVAL
        ).count()

    return context