from collections import defaultdict
from decimal import Decimal
from django.dispatch import receiver
from django.http import HttpRequest
from django.urls import resolve, reverse
from django.utils.translation import gettext, gettext_lazy as _
from pretix.base.decimal import round_decimal
from pretix.base.models import CartPosition, Event, TaxRule
from pretix.base.models.orders import OrderFee
from pretix.base.settings import settings_hierarkey
from pretix.base.signals import order_fee_calculation
from pretix.base.templatetags.money import money_filter
from pretix.control.signals import nav_event_settings
from pretix.presale.signals import (
    fee_calculation_for_cart, front_page_top, order_meta_from_request,
)
from pretix.presale.views import get_cart
from pretix.presale.views.cart import cart_session


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


def get_fees(event, total, invoice_address, mod='', request=None, positions=[], gift_cards=None, payment_requests=None):
    if request is not None and not positions:
        positions = get_cart(request)

    skip_free = event.settings.get('service_fee_skip_free', as_type=bool)
    if skip_free:
        positions = [pos for pos in positions if pos.price != Decimal('0.00')]

    skip_addons = event.settings.get('service_fee_skip_addons', as_type=bool)
    if skip_addons:
        positions = [pos for pos in positions if not pos.addon_to_id]

    skip_non_admission = event.settings.get('service_fee_skip_non_admission', as_type=bool)
    if skip_non_admission:
        positions = [pos for pos in positions if pos.item.admission]

    fee_per_ticket = event.settings.get('service_fee_per_ticket' + mod, as_type=Decimal)
    if mod and fee_per_ticket is None:
        fee_per_ticket = event.settings.get('service_fee_per_ticket', as_type=Decimal)

    fee_abs = event.settings.get('service_fee_abs' + mod, as_type=Decimal)
    if mod and fee_abs is None:
        fee_abs = event.settings.get('service_fee_abs', as_type=Decimal)

    fee_percent = event.settings.get('service_fee_percent' + mod, as_type=Decimal)
    if mod and fee_percent is None:
        fee_percent = event.settings.get('service_fee_percent', as_type=Decimal)

    fee_per_ticket = Decimal("0") if fee_per_ticket is None else fee_per_ticket
    fee_abs = Decimal("0") if fee_abs is None else fee_abs
    fee_percent = Decimal("0") if fee_percent is None else fee_percent

    if event.settings.get('service_fee_skip_if_gift_card', as_type=bool):
        if payment_requests is not None:
            for p in payment_requests:
                if p['provider'] == 'giftcard':
                    total = max(0, total - Decimal(p['max_value'] or '0'))

        else:
            # pretix pre 4.15
            gift_cards = gift_cards or []
            if request:
                cs = cart_session(request)
                if cs.get('gift_cards'):
                    gift_cards = event.organizer.accepted_gift_cards.filter(pk__in=cs.get('gift_cards'), currency=event.currency)
            summed = 0
            for gc in gift_cards:
                fval = Decimal(gc.value)  # TODO: don't require an extra query
                fval = min(fval, total - summed)
                if fval > 0:
                    total -= fval
                    summed += fval

    # This hack allows any payment provider to declare a setting service_fee_skip_if_{pprovname} in order to implement
    # the skipping of service fees when they are paid in their entirety through said payment provider/method.
    # It is notably used by the KulturPass, which is for all intents and purposes a giftcard but handled like a regular
    # payment provider.
    if payment_requests is not None:
        for p in payment_requests:
            if event.settings.get(f'service_fee_skip_if_{p["provider"]}', default=False, as_type=bool):
                total = max(0, total - Decimal(p['max_value'] or '0'))

    if (fee_per_ticket or fee_abs or fee_percent) and total != Decimal('0.00'):
        tax_rule_zero = TaxRule.zero()
        fee = round_decimal(fee_abs + total * (fee_percent / 100) + len(positions) * fee_per_ticket, event.currency)
        split_taxes = event.settings.get('service_fee_split_taxes', as_type=bool)
        if split_taxes:
            # split taxes based on products ordered
            d = defaultdict(lambda: Decimal('0.00'))
            for p in positions:
                if isinstance(p, CartPosition):
                    tr = p.item.tax_rule
                else:
                    tr = p.tax_rule
                d[tr] += p.price - p.tax_value

            base_values = sorted([tuple(t) for t in d.items()], key=lambda t: t[0].rate)
            sum_base = sum(t[1] for t in base_values)
            if sum_base:
                fee_values = [(t[0], round_decimal(fee * t[1] / sum_base, event.currency))
                              for t in base_values]
                sum_fee = sum(t[1] for t in fee_values)

                # If there are rounding differences, we fix them up, but always leaning to the benefit of the tax
                # authorities
                if sum_fee > fee:
                    fee_values[0] = (fee_values[0][0], fee_values[0][1] + (fee - sum_fee))
                elif sum_fee < fee:
                    fee_values[-1] = (fee_values[-1][0], fee_values[-1][1] + (fee - sum_fee))
            else:
                fee_values = [(event.settings.tax_rate_default or tax_rule_zero, fee)]

        else:
            fee_values = [(event.settings.tax_rate_default or tax_rule_zero, fee)]

        fees = []
        for tax_rule, price in fee_values:
            tax_rule = tax_rule or tax_rule_zero
            tax = tax_rule.tax(price, invoice_address=invoice_address, base_price_is='gross')
            fees.append(OrderFee(
                fee_type=OrderFee.FEE_TYPE_SERVICE,
                internal_type='',
                value=price,
                tax_rate=tax.rate,
                tax_value=tax.tax,
                tax_rule=tax_rule
            ))
        return fees

    return []


@receiver(fee_calculation_for_cart, dispatch_uid="service_fee_calc_cart")
def cart_fee(sender: Event, request: HttpRequest, invoice_address, total, **kwargs):
    mod = ''
    try:
        from pretix_resellers.utils import (
            ResellerException, get_reseller_and_user,
        )
    except ImportError:
        pass
    else:
        try:
            reseller, user = get_reseller_and_user(request)
            config = reseller.configs.get(organizer_id=sender.organizer_id)
            if config.skip_default_service_fees:
                return []
        except ResellerException:
            pass
        else:
            mod = '_resellers'
    return get_fees(sender, total, invoice_address, mod, request, payment_requests=kwargs.get('payment_requests'))


@receiver(order_fee_calculation, dispatch_uid="service_fee_calc_order")
def order_fee(sender: Event, positions, invoice_address, total, meta_info, gift_cards, **kwargs):
    mod = ''
    if meta_info.get('servicefees_reseller_id'):
        mod = '_resellers'
        try:
            from pretix_resellers.models import Reseller
        except ImportError:
            pass
        else:
            r = Reseller.objects.get(pk=meta_info.get('servicefees_reseller_id'))
            config = r.configs.get(organizer_id=sender.organizer_id)
            if config.skip_default_service_fees:
                return []

    return get_fees(sender, total, invoice_address, mod, positions=positions, gift_cards=gift_cards,
                    payment_requests=kwargs.get('payment_requests'))


@receiver(front_page_top, dispatch_uid="service_fee_front_page_top")
def front_page_top_recv(sender: Event, **kwargs):
    fees = []
    fee_per_ticket = sender.settings.get('service_fee_per_ticket', as_type=Decimal)
    if fee_per_ticket:
        fees = fees + ["{} {}".format(money_filter(fee_per_ticket, sender.currency), gettext('per ticket'))]

    fee_abs = sender.settings.get('service_fee_abs', as_type=Decimal)
    if fee_abs:
        fees = fees + ["{} {}".format(money_filter(fee_abs, sender.currency), gettext('per order'))]

    fee_percent = sender.settings.get('service_fee_percent', as_type=Decimal)
    if fee_percent:
        fees = fees + ['{} % {}'.format(fee_percent, gettext('per order'))]

    if fee_per_ticket or fee_abs or fee_percent:
        return '<p>%s</p>' % gettext('A service fee of {} will be added to the order total.').format(
            ' {} '.format(gettext('plus')).join(fees)
        )


@receiver(order_meta_from_request, dispatch_uid="servicefees_order_meta")
def order_meta_signal(sender: Event, request: HttpRequest, **kwargs):
    meta = {}
    try:
        from pretix_resellers.utils import (
            ResellerException, get_reseller_and_user,
        )
    except ImportError:
        pass
    else:
        try:
            reseller, user = get_reseller_and_user(request)
            meta['servicefees_reseller_id'] = reseller.pk
        except ResellerException:
            pass
    return meta


settings_hierarkey.add_default('service_fee_skip_addons', 'True', bool)
settings_hierarkey.add_default('service_fee_skip_free', 'True', bool)
