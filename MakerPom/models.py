from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class CreatPom(models.Model):
    AWAITING_APPROVAL = "w"
    APPROVED = "a"
    REJECTED = "r"

    STATUS_CHOICES = (
        (AWAITING_APPROVAL, _("Awaiting Approval")),
        (APPROVED, _("Approved")),
        (REJECTED, _("Rejected")),
    )

    POEM_TYPES = (
        ("ghazal", _("Ghazal")),
        ("masnavi", _("Masnavi")),
        ("robaee", _("Robaee")),
        ("ghasideh", _("Ghasideh")),
        ("nimaee", _("Nimaee")),
        ("sepid", _("Sepid")),
    )

    name = models.CharField(_("Poem Name"), max_length=150)
    text = models.TextField(verbose_name=_("Poem Text"))
    voies = models.FileField(upload_to="Voies/", verbose_name=_("Audio File"))
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="author",
        verbose_name=_("Author"),
    )
    status = models.CharField(
        verbose_name=_("Status"),
        choices=STATUS_CHOICES,
        max_length=1,
        blank=True,
        default=AWAITING_APPROVAL,
    )
    poem_type = models.CharField(
        verbose_name=_("Poem Type"),
        choices=POEM_TYPES,
        max_length=20,
        blank=True,
        default=_("Ghazal"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text[:10]

    def get_absolute_url(self):
        return reverse("detail_poem", kwargs={"pk": self.pk})

    class Meta:
        indexes = [
            models.Index(fields=["status"], name="creatpom_status_idx"),
        ]