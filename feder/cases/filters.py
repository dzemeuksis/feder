import django_filters
from dal import autocomplete
from django import forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from teryt_tree.dal_ext.filters import VoivodeshipFilter, CountyFilter, CommunityFilter

from .models import Case
from feder.main.mixins import DisabledWhenFilterSetMixin
from feder.teryt.filters import (
    DisabledWhenVoivodeshipFilter,
    DisabledWhenCountyFilter,
    DisabledWhenCommunityFilter,
)
from feder.cases_tags.models import Tag
from feder.monitorings.models import Monitoring


class CaseFilter(DisabledWhenFilterSetMixin, django_filters.FilterSet):
    created = django_filters.DateRangeFilter(label=_("Creation date"))
    voivodeship = DisabledWhenVoivodeshipFilter()
    county = DisabledWhenCountyFilter()
    community = DisabledWhenCommunityFilter()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["name"].lookup_expr = "icontains"
        self.filters["name"].label = _("Name")
        self.filters["monitoring"].field.widget = autocomplete.ModelSelect2(
            url="monitorings:autocomplete"
        )
        self.filters["institution"].field.widget = autocomplete.ModelSelect2(
            url="institutions:autocomplete"
        )

    class Meta:
        model = Case
        fields = [
            "name",
            "monitoring",
            "institution",
            "created",
            "confirmation_received",
            "response_received",
        ]


class CaseReportFilter(django_filters.FilterSet):
    monitoring = django_filters.ModelChoiceFilter(queryset=Monitoring.objects.all())
    name = django_filters.CharFilter(
        label=_("Institution name"),
        field_name="institution__name",
        lookup_expr="icontains",
    )
    voivodeship = VoivodeshipFilter(
        widget=autocomplete.ModelSelect2(url="teryt:voivodeship-autocomplete")
    )
    county = CountyFilter(
        widget=autocomplete.ModelSelect2(
            url="teryt:county-autocomplete", forward=["voivodeship"]
        )
    )
    community = CommunityFilter(
        widget=autocomplete.ModelSelect2(
            url="teryt:community-autocomplete", forward=["county"]
        )
    )
    tags = django_filters.ModelMultipleChoiceFilter(
        label=_("Tags"), field_name="tags", widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data, queryset, request=request, prefix=prefix)
        case = queryset.first()
        self.filters["tags"].queryset = (
            Tag.objects.filter(
                Q(monitoring__isnull=True) | Q(monitoring=case.monitoring)
            )
            if case
            else Tag.objects.none()
        )

    class Meta:
        model = Case
        fields = [
            "monitoring",
            "name",
            "voivodeship",
            "county",
            "community",
            "tags",
            "confirmation_received",
            "response_received",
        ]
