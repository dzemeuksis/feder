from django.utils import formats
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from feder.cases.models import Case


class CaseSerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Case
        fields = (
            "pk",
            "name",
            "user",
            "institution",
            "monitoring",
            "created",
            "modified",
        )


class CaseReportSerializer(serializers.HyperlinkedModelSerializer):
    institution_name = serializers.SerializerMethodField()
    institution_email = serializers.SerializerMethodField()
    institution_regon = serializers.SerializerMethodField()
    community = serializers.CharField(source="institution.community")
    county = serializers.CharField(source="institution.county")
    voivodeship = serializers.CharField(source="institution.voivodeship")
    tags = serializers.CharField(source="tags_str")
    request_date = serializers.SerializerMethodField()
    confirmation_received = serializers.SerializerMethodField()
    response_received = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = (
            "pk",
            "institution_name",
            "institution_email",
            "institution_regon",
            "voivodeship",
            "county",
            "community",
            "tags",
            "request_date",
            "confirmation_received",
            "response_received",
        )

    def get_institution_name(self, obj):
        return obj.institution.name

    def get_institution_email(self, obj):
        return obj.institution.email

    def get_institution_regon(self, obj):
        return obj.institution.regon

    def get_request_date(self, obj):
        letter = obj.application_letter
        return formats.date_format(letter.created, format="Y-m-d") if letter else None

    def get_confirmation_received(self, obj):
        return _("yes") if obj.confirmation_received else _("no")

    def get_response_received(self, obj):
        return _("yes") if obj.response_received else _("no")
