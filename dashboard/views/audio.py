from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView, View

from dashboard.forms import AudioReplaceForm
from dashboard.mixins import ContentManagerAccessMixin, DashboardSuccessMessageMixin
from dashboard.services import PoemManagementService
from MakerPom.models import CreatPom


class AudioReplaceView(
    ContentManagerAccessMixin,
    DashboardSuccessMessageMixin,
    UpdateView,
):
    """Replace the audio file of a poem."""
    model = CreatPom
    form_class = AudioReplaceForm
    template_name = 'dashboard/audio_replace.html'
    success_message = _('Audio replaced successfully.')

    def get_success_url(self):
        return reverse_lazy('dashboard:poem_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        """Remove 'instance' because AudioReplaceForm is not a ModelForm."""
        kwargs = super().get_form_kwargs()
        kwargs.pop('instance', None)
        return kwargs

    def form_valid(self, form):
        poem = self.get_object()
        service = PoemManagementService()
        service.replace_audio(poem, self.request.user, form.cleaned_data['voies'])
        # UpdateView expects self.object to be set; use the poem as object
        self.object = poem
        return super().form_valid(form)


class AudioDeleteView(ContentManagerAccessMixin, View):
    """Delete the audio file of a poem."""
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        poem = get_object_or_404(CreatPom, pk=kwargs['pk'])
        service = PoemManagementService()
        try:
            service.delete_audio(poem, request.user)
            messages.success(request, _('Audio deleted.'))
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('dashboard:poem_detail', pk=poem.pk)