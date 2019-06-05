from django.apps import AppConfig
from django.utils.translation import ugettext_lazy


class PluginApp(AppConfig):
    name = 'pretix_servicefees'
    verbose_name = 'pretix Service Fees'

    class PretixPluginMeta:
        name = ugettext_lazy('pretix Service Fees')
        author = 'Raphael Michel'
        description = ugettext_lazy('This plugin allows to charge a service fee on all non-free orders.')
        visible = True
        version = '1.3.1'

    def ready(self):
        from . import signals  # NOQA


default_app_config = 'pretix_servicefees.PluginApp'
