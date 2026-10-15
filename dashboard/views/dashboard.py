from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from dashboard.mixins import ContentManagerAccessMixin
from dashboard.models import ContentActivityLog
from MakerPom.models import CreatPom


class DashboardIndexView(ContentManagerAccessMixin, TemplateView):
    """Main dashboard overview with summary counts and recent activity."""

    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ---------------------------------------------------------
        # Poem Statistics
        # ---------------------------------------------------------
        poem_stats = CreatPom.objects.aggregate(
            total_poems=Count("id"),
            awaiting_approval=Count(
                "id",
                filter=Q(
                    status=CreatPom.AWAITING_APPROVAL
                ),
            ),
            approved_poems=Count(
                "id",
                filter=Q(
                    status=CreatPom.APPROVED
                ),
            ),
            rejected_poems=Count(
                "id",
                filter=Q(
                    status=CreatPom.REJECTED
                ),
            ),
        )

        # ---------------------------------------------------------
        # Recent Activity
        # ---------------------------------------------------------
        recent_activity = (
            ContentActivityLog.objects
            .select_related("manager", "poem")[:5]
        )

        # ---------------------------------------------------------
        # Context
        # ---------------------------------------------------------
        context.update({
            **poem_stats,
            "recent_activity": recent_activity,
            "page_title": _("Dashboard"),
        })

        return context


