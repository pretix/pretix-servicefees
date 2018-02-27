from django import forms
from django.urls import reverse

from pretix.base.forms import SettingsForm
from pretix.base.models import Event
from pretix.control.views.event import EventSettingsViewMixin, EventSettingsFormView

class ServiceFeeSettingsForm(SettingsForm):
    service_fee_abs = forms.DecimalField()


class SettingsView(EventSettingsViewMixin, EventSettingsFormView):
    model = Event
    form_class = ServiceFeeSettingsForm
    template_name = 'pretix_servicefees/settings.html'
    permission = 'can_change_event_settings'

    def get_success_url(self) -> str:
        return reverse('plugins:pretix_servicefees:settings', kwargs={
            'organizer': self.request.event.organizer.slug,
            'event': self.request.event.slug
        })
