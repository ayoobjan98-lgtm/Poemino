# dashboard/views/poems.py

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, UpdateView, View

from dashboard.forms import PoemEditForm
from dashboard.mixins import (
    ContentManagerAccessMixin,
    DashboardPaginationMixin,
    DashboardSuccessMessageMixin,
)
from dashboard.models import ContentActivityLog
from dashboard.services import PoemManagementService
from MakerPom.models import CreatPom
from MakerPom.services import (
    build_poem_queryset,
    get_filter_params,
    InvalidPoemDateError,
)


class PoemListView(ContentManagerAccessMixin, DashboardPaginationMixin, ListView):
    model = CreatPom
    template_name = "dashboard/poem_list.html"
    context_object_name = "poems"
    ordering = ["-created_at"]

    def get_queryset(self):
        base = CreatPom.objects.select_related("author").all()
        params, chips = get_filter_params(self.request)
        print("FIlter : %s | %s" % (params, chips))
        self.filter_chips = chips
        self.filter_params = params
        self.invalid_date = False
        self.poem_date_search = bool(params.get("poem_date"))
        try:
            return build_poem_queryset(base, params).order_by("-created_at")
        except InvalidPoemDateError:
            self.invalid_date = True
            return base.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_chips"] = getattr(self, "filter_chips", [])
        context["filter_params"] = getattr(self, "filter_params", {})
        context["invalid_date"] = getattr(self, "invalid_date", False)
        context["poem_date_search"] = getattr(self, "poem_date_search", False)
        context["poem_type_choices"] = CreatPom.POEM_TYPES
        context["page_title"] = _("Poem Management")
        context["current_status"] = self.request.GET.get("status", "")
        return context


class PoemDetailView(ContentManagerAccessMixin, DetailView):
    model = CreatPom
    template_name = "dashboard/poem_detail.html"
    context_object_name = "poem"

    def get_queryset(self):
        return super().get_queryset().select_related("author")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["activity_logs"] = (
            ContentActivityLog.objects
            .filter(poem=self.object)
            .select_related("manager", "poem")
            .order_by("-timestamp")[:20]
        )
        context["page_title"] = self.object.name
        return context


class PoemEditView(ContentManagerAccessMixin, DashboardSuccessMessageMixin, UpdateView):
    model = CreatPom
    form_class = PoemEditForm
    template_name = "dashboard/poem_edit.html"
    success_message = _("Poem updated successfully.")

    def get_queryset(self):
        return super().get_queryset().select_related("author")

    def get_success_url(self):
        return reverse_lazy("dashboard:poem_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        service = PoemManagementService()
        service.edit_poem(
            poem=self.object,
            manager=self.request.user,
            name=form.cleaned_data["name"],
            text=form.cleaned_data["text"],
        )
        return response


class PoemApproveView(ContentManagerAccessMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        poem = get_object_or_404(CreatPom, pk=kwargs["pk"])
        service = PoemManagementService()
        try:
            service.approve_poem(poem, request.user)
            messages.success(request, _("Poem approved successfully."))
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:poem_detail", pk=poem.pk)


class PoemRejectView(ContentManagerAccessMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        poem = get_object_or_404(CreatPom, pk=kwargs["pk"])
        reason = request.POST.get("reason", "")
        service = PoemManagementService()
        try:
            service.reject_poem(poem, request.user, reason=reason)
            messages.success(request, _("Poem rejected."))
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:poem_detail", pk=poem.pk)


class PoemDeleteView(ContentManagerAccessMixin, View):
    """Hard delete — permanently removes the poem and its activity logs."""
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        poem = get_object_or_404(CreatPom, pk=kwargs["pk"])
        poem.delete()
        messages.success(request, _("Poem deleted."))
        return redirect("dashboard:poem_list")


class PoemRestoreView(ContentManagerAccessMixin, View):
    """
    Return a rejected poem to the review queue.

    Only handles REJECTED -> AWAITING_APPROVAL.
    """
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        poem = get_object_or_404(CreatPom, pk=kwargs["pk"])
        service = PoemManagementService()

        if poem.status == CreatPom.REJECTED:
            try:
                service.return_rejected_to_review(poem, request.user)
                messages.success(
                    request,
                    _("Poem returned to the review queue."),
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:poem_detail", pk=poem.pk)

        messages.info(request, _("Nothing to restore for this poem."))
        return redirect("dashboard:poem_detail", pk=poem.pk)
# END