from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    CreateView,
    UpdateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.translation import gettext_lazy as _

from .models import CreatPom
from .forms import CreatePomForm
from .services import (
    build_poem_queryset,
    get_filter_params,
    InvalidPoemDateError,
)


class HomeView(ListView):
    model = CreatPom
    template_name = "index.html"
    context_object_name = "poms"
    paginate_by = 10
    ordering = ["-created_at"]

    def get_queryset(self):
        # build_poem_queryset() already applies select_related("author"),
        # so no N+1 queries occur when the template accesses poem.author.
        base = CreatPom.objects.select_related("author").filter(status="a")
        params, chips = get_filter_params(self.request)
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
        context["user"] = self.request.user

        # Only run the pending-poem count when the user is authenticated.
        if self.request.user.is_authenticated:
            context["count"] = CreatPom.objects.filter(
                author=self.request.user, status="w"
            ).count()
        else:
            context["count"] = 0
        return context


class AddPoemView(LoginRequiredMixin, CreateView):
    model = CreatPom
    form_class = CreatePomForm
    template_name = "add.html"
    success_url = "/"
    login_url = reverse_lazy("login")

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form):
        if not self.request.user.is_authenticated:
            return redirect("login")
        return super().form_invalid(form)


class PoemDetailView(DetailView):
    model = CreatPom
    template_name = "detail-poem.html"
    context_object_name = "poem"

    def get_queryset(self):
        # Join author once so the template avoids an N+1 query.
        return super().get_queryset().select_related("author")


class PoemUpdateView(UserPassesTestMixin, UpdateView):
    model = CreatPom
    form_class = CreatePomForm
    context_object_name = "poem"
    template_name = "poem_update.html"

    def get_queryset(self):
        return super().get_queryset().select_related("author")

    def test_func(self):
        poem = self.get_object()
        return self.request.user == poem.author

    def get_success_url(self):
        return reverse_lazy("poem_detail", kwargs={"pk": self.object.pk})


class PoemDeleteView(LoginRequiredMixin, DeleteView):
    model = CreatPom
    context_object_name = "poem"
    template_name = "poem_delete.html"
    success_url = reverse_lazy("MakePoem:recent_poems")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset).select_related("author")
        if obj.author != self.request.user:
            raise Http404(_("Poem not found"))
        return obj


class RecentPoemsView(ListView):
    model = CreatPom
    template_name = "recent.html"
    context_object_name = "poems"
    paginate_by = 5
    ordering = ["-created_at"]

    def get_queryset(self):
        base = CreatPom.objects.select_related('author').filter(status="a")
        params, chips = get_filter_params(self.request)
        self.filter_chips = chips
        self.filter_params = params
        self.invalid_date = False
        self.poem_date_search = bool(params.get("poem_date"))

        has_filter = any(
            params.get(k)
            for k in ["q", "author", "title", "poem_type", "poem_date", "status"]
        )

        try:
            qs = build_poem_queryset(base, params).order_by("-created_at")
        except InvalidPoemDateError:
            self.invalid_date = True
            return base.none()

        if not has_filter:
            qs = qs[:5]
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_chips"] = getattr(self, "filter_chips", [])
        context["filter_params"] = getattr(self, "filter_params", {})
        context["invalid_date"] = getattr(self, "invalid_date", False)
        context["poem_date_search"] = getattr(self, "poem_date_search", False)
        return context


class NotFoundPageView(TemplateView):
    template_name = "404.html"

