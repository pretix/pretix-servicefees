from decimal import Decimal

from django.urls import resolve, reverse
from django.dispatch import receiver
from django.http import HttpRequest
from django.utils.translation import ugettext_lazy as _, ugettext, get_language
from pretix.base.models import Event, Order, TaxRule
from pretix.base.models.orders import OrderFee
from pretix.base.signals import order_fee_calculation
from pretix.base.templatetags.money import money_filter
from pretix.control.signals import nav_event_settings
from pretix.presale.signals import fee_calculation_for_cart, front_page_top, order_meta_from_request


@receiver(nav_event_settings, dispatch_uid='service_fee_nav_settings')
def navbar_settings(sender, request, **kwargs):
    url = resolve(request.path_info)
    return [{
        'label': _('Service Fee'),
        'url': reverse('plugins:pretix_servicefees:settings', kwargs={
            'event': request.event.slug,
            'organizer': request.organizer.slug,
        }),
        'active': url.namespace == 'plugins:pretix_servicefees' and url.url_name.startswith('settings'),
    }]


def get_fees(event, total, invoice_address, mod=''):
    fee_abs = event.settings.get('service_fee_abs' + mod, as_type=Decimal)
    if mod and fee_abs is None:
        fee_abs = event.settings.get('service_fee_abs', as_type=Decimal)

    fee_percent = event.settings.get('service_fee_percent' + mod, as_type=Decimal)
    if mod and fee_percent is None:
        fee_percent = event.settings.get('service_fee_percent', as_type=Decimal)

    if fee_abs and fee_percent and total != Decimal('0.00'):
        fee = fee_abs + total * (fee_percent / 100)
        tax_rule = event.settings.tax_rate_default or TaxRule.zero()
        if tax_rule.tax_applicable(invoice_address):
            tax = tax_rule.tax(fee)
            return [OrderFee(
                fee_type=OrderFee.FEE_TYPE_SERVICE,
                internal_type='',
                value=fee,
                tax_rate=tax.rate,
                tax_value=tax.tax,
                tax_rule=tax_rule
            )]
        else:
            return [OrderFee(
                fee_type=OrderFee.FEE_TYPE_SERVICE,
                internal_type='',
                value=fee,
                tax_rate=Decimal('0.00'),
                tax_value=Decimal('0.00'),
                tax_rule=tax_rule
            )]
    return []


@receiver(fee_calculation_for_cart, dispatch_uid="service_fee_calc_cart")
def cart_fee(sender: Event, request: HttpRequest, invoice_address, total, **kwargs):
    mod = ''
    try:
        from pretix_resellers.utils import ResellerException, get_reseller_and_user
    except ImportError:
        pass
    else:
        try:
            get_reseller_and_user(request)
        except ResellerException:
            pass
        else:
            mod = '_resellers'
    return get_fees(sender, total, invoice_address, mod)


@receiver(order_fee_calculation, dispatch_uid="service_fee_calc_order")
def order_fee(sender: Event, invoice_address, total, meta_info, **kwargs):
    mod = ''
    if meta_info.get('servicefees_reseller_id'):
        mod = '_resellers'
    return get_fees(sender, total, invoice_address, mod)


@receiver(front_page_top, dispatch_uid="service_fee_front_page_top")
def front_page_top_recv(sender: Event, **kwargs):
    fee = sender.settings.get('service_fee_abs', as_type=Decimal)
    if fee:
        return '<p>%s</p>' % ugettext('A service fee of {} will be added on top of each order.').format(
            money_filter(fee, sender.currency)
        )


@receiver(order_meta_from_request, dispatch_uid="servicefees_order_meta")
def order_meta_signal(sender: Event, request: HttpRequest, **kwargs):
    meta = {}
    try:
        from pretix_resellers.utils import ResellerException, get_reseller_and_user
    except ImportError:
        pass
    else:
        try:
            user, reseller = get_reseller_and_user(request)
            meta['servicefees_reseller_id'] = reseller.pk
        except ResellerException:
            pass
    return meta
