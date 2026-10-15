from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from dashboard.mixins import ContentManagerAccessMixin


class VoiceToTextView(ContentManagerAccessMixin, TemplateView):
    """Live microphone-to-text tool for content managers."""
    template_name = 'dashboard/voice_to_text.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Voice to Text')
        return context