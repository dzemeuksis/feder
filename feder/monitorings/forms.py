# -*- coding: utf-8 -*-
from atom.ext.guardian.forms import TranslatedUserObjectPermissionsForm
from atom.ext.crispy_forms.forms import SingleButtonMixin
from braces.forms import UserKwargModelFormMixin
from crispy_forms.layout import Fieldset, Layout
from django import forms
from django.utils.translation import ugettext as _
from dal import autocomplete
from .models import Monitoring
from feder.users.models import User


class MonitoringForm(SingleButtonMixin, UserKwargModelFormMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(MonitoringForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Monitoring
        fields = ['name', 'description', 'notify_alert']


class SelectUserForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=autocomplete.ModelSelect2(url='users:user-autocomplete'),
        label=_("User")
    )


class SaveTranslatedUserObjectPermissionsForm(SingleButtonMixin,
                                              TranslatedUserObjectPermissionsForm):
    pass
