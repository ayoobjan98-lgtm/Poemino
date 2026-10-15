from .models import CreatPom


def poem_choice_context(request):
    """
    Expose poem types and statuses to all templates.
    """
    return {
        'POEM_TYPES': CreatPom.POEM_TYPES,
        'POEM_STATUS_CHOICES': CreatPom.STATUS_CHOICES,
    }