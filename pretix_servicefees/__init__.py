from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class PluginApp(AppConfig):
    name = 'pretix_servicefees'
    verbose_name = 'Service Fees'

    class PretixPluginMeta:
        name = gettext_lazy('Service Fees')
        author = 'Raphael Michel'
        category = 'FEATURE'
        description = gettext_lazy('This plugin allows to charge a service fee on all non-free orders.')
        visible = True
        version = '1.7.0'

    def ready(self):
        from . import signals  # NOQA


default_app_config = 'pretix_servicefees.PluginApp'
