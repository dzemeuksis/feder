import json
from collections import OrderedDict

from django.db import models
from django.db.models import Count
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from jsonfield import JSONField
from model_utils import Choices
from model_utils.models import TimeStampedModel

from feder.cases.models import Case
from feder.letters.models import Letter

STATUS = Choices(
    ("open", _("Open")),
    ("ok", _("Delivered")),
    ("spambounce", _("Spam-bounce")),
    ("softbounce", _("Soft-bounce")),
    ("hardbounce", _("Hard-bounce")),
    ("dropped", _("Dropped")),
    ("deferred", _("Deferred")),
    ("unknown", _("Unknown")),
)


class EmailQuerySet(models.QuerySet):
    def with_logrecord_count(self):
        return self.annotate(Count("logrecord"))


class EmailLog(TimeStampedModel):
    status = models.CharField(choices=STATUS, default=STATUS.unknown, max_length=20)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, max_length=_("Case"))
    letter = models.OneToOneField(
        Letter, on_delete=models.CASCADE, max_length=_("Letter"), null=True, blank=True
    )
    email_id = models.CharField(verbose_name=_("Message-ID"), max_length=255)
    to = models.CharField(verbose_name=_("To"), max_length=255)
    objects = EmailQuerySet.as_manager()

    def __str__(self):
        return f"Email #{self.pk} ({self.email_id})"

    @property
    def status_verbose(self):
        return dict(STATUS)[self.status]

    def get_absolute_url(self):
        return reverse("logs:detail", kwargs={"pk": self.pk})

    class Meta:
        verbose_name = _("Email log")
        verbose_name_plural = _("Email logs")
        ordering = ["created"]


class LogRecordQuerySet(models.QuerySet):
    def parse_rows(self, rows):
        skipped, saved = 0, 0
        cases = dict(
            Letter.objects.filter(record__case__isnull=False).values_list(
                "record__case__email", "record__case_id"
            )
        )
        letters = dict(
            Letter.objects.is_outgoing().values_list("message_id_header", "id")
        )

        for row in rows:
            if row["from"] not in cases:
                skipped += 1
                continue
            log = LogRecord(data=row)
            status = log.get_status()
            letter = letters.get(row["message_id"], None)
            obj, created = EmailLog.objects.get_or_create(
                case_id=cases[row["from"]],
                email_id=row["id"],
                to=row["to"],
                defaults={"status": status, "letter_id": letter},
            )
            if obj.status != status:
                obj.status = status
                obj.save(update_fields=["status"])
            log.email = obj
            log.save()
            saved += 1
        return skipped, saved


class LogRecord(TimeStampedModel):
    email = models.ForeignKey(
        EmailLog, on_delete=models.CASCADE, verbose_name=_("Email")
    )
    data = JSONField()
    objects = LogRecordQuerySet.as_manager()

    def get_status(self):
        status_list = OrderedDict(STATUS).keys()
        for status in status_list:
            time_name = f"{status}_time"
            desc_name = f"{status}_desc"
            if self.data.get(time_name, False) or self.data.get(desc_name, False):
                return status
        return STATUS.unknown

    def pretty_json(self):
        return json.dumps(self.data, indent=4)

    class Meta:
        verbose_name = _("Log record")
        verbose_name_plural = _("Log records")
        ordering = ["created"]

    def __str__(self):
        return f"Log #{self.pk} for email #{self.email_id}"
