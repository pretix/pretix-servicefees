from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from pretix.base.forms import SettingsForm
from pretix.base.models import Event
from pretix.control.views.event import EventSettingsViewMixin, EventSettingsFormView
from pretix.helpers.money import change_decimal_field


class ServiceFeeSettingsForm(SettingsForm):
    service_fee_abs = forms.DecimalField(
        label=_('Fixed fee per order'),
        required=False
    )
    service_fee_percent = forms.DecimalField(
        label=_('Percentual fee per order'),
        help_text=_('Percentage of the order total. Note that this percentage will currently only '
                    'be calculated on the summed price of sold tickets, not on other fees like e.'
                    'g. shipping fees, if there are any.'),
        required=False
    )
    service_fee_per_ticket = forms.DecimalField(
        label=_('Fixed fee per ticket'),
        help_text=_('This fee will be added for each ticket sold, except for free items and addons.'),
        required=False
    )

    service_fee_abs_resellers = forms.DecimalField(
        label=_('Fixed fee per order'),
        required=False
    )
    service_fee_percent_resellers = forms.DecimalField(
        label=_('Percentual fee per order'),
        help_text=_('Percentage of the order total. Note that this percentage will currently only '
                    'be calculated on the summed price of sold tickets, not on other fees like e.'
                    'g. shipping fees, if there are any.'),
        required=False
    )
    service_fee_per_ticket_resellers = forms.DecimalField(
        label=_('Fixed fee per ticket'),
        required=False,
        help_text=_('This fee will be added for each ticket sold, except for free items and addons.')
    )


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
