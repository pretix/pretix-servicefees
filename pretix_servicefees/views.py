from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pretix.base.forms import SettingsForm
from pretix.base.models import Event
from pretix.control.views.event import (
    EventSettingsFormView,
    EventSettingsViewMixin,
)


class ServiceFeeSettingsForm(SettingsForm):
    service_fee_abs = forms.DecimalField(label=_("Fixed fee per order"), required=False)
    service_fee_percent = forms.DecimalField(
        label=_("Percentual fee per order"),
        help_text=_(
            "Percentage of the order total. Note that this percentage will currently only "
            "be calculated on the summed price of sold tickets, not on other fees like e."
            "g. shipping fees, if there are any."
        ),
        required=False,
    )
    service_fee_per_ticket = forms.DecimalField(
        label=_("Fixed fee per ticket"),
        help_text=_(
            "This fee will be added for each ticket sold, except for free items and addons."
        ),
        required=False,
    )
    service_fee_skip_if_gift_card = forms.BooleanField(
        label=_("Do not charge service fee on tickets paid with gift cards"),
        help_text=_(
            "If a gift card is used for the payment, the percentual fees will be applied on the value of the "
            "tickets minus the value of the gift cards. All fixed fees will be dropped if the tickets can "
            "be paid with gift cards entirely. This only works if the gift card is redeemd when the order is "
            "submitted, not if it's used to pay an unpaid order later."
        ),
        required=False,
    )
    service_fee_skip_addons = forms.BooleanField(
        label=_("Do not charge per-ticket service fee on add-on products"),
        required=False,
    )
    service_fee_skip_non_admission = forms.BooleanField(
        label=_("Do not charge per-ticket service fee on non-admission products"),
        required=False,
    )
    service_fee_skip_free = forms.BooleanField(
        label=_("Do not charge per-ticket service fee on free products"),
        help_text=_(
            "Note that regardless of this setting, a per-ticket fee will not be charged if the entire order is free."
        ),
        required=False,
    )
    service_fee_split_taxes = forms.BooleanField(
        label=_(
            "Split taxes proportionate to the tax rates and net values of the ordered products."
        ),
        help_text=_(
            "If not split based on ordered products, the tax rate falls back to the event’s default tax rate or no tax, if no default tax rate exists."
        ),
        required=False,
    )

    service_fee_abs_resellers = forms.DecimalField(
        label=_("Fixed fee per order"), required=False
    )
    service_fee_percent_resellers = forms.DecimalField(
        label=_("Percentual fee per order"),
        help_text=_(
            "Percentage of the order total. Note that this percentage will currently only "
            "be calculated on the summed price of sold tickets, not on other fees like e."
            "g. shipping fees, if there are any."
        ),
        required=False,
    )
    service_fee_per_ticket_resellers = forms.DecimalField(
        label=_("Fixed fee per ticket"),
        required=False,
        help_text=_(
            "This fee will be added for each ticket sold, except for free items and addons."
        ),
    )


class SettingsView(EventSettingsViewMixin, EventSettingsFormView):
    model = Event
    form_class = ServiceFeeSettingsForm
    template_name = "pretix_servicefees/settings.html"
    permission = "can_change_event_settings"

    def get_success_url(self) -> str:
        return reverse(
            "plugins:pretix_servicefees:settings",
            kwargs={
                "organizer": self.request.event.organizer.slug,
                "event": self.request.event.slug,
            },
        )
