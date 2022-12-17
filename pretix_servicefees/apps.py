from django.apps import AppConfig
from django.utils.translation import gettext_lazy
from . import __version__


class PluginApp(AppConfig):
    name = 'pretix_servicefees'
    verbose_name = 'Service Fees'

    class PretixPluginMeta:
        name = gettext_lazy('Service Fees')
        author = 'Raphael Michel'
        category = 'FEATURE'
        description = gettext_lazy('This plugin allows to charge a service fee on all non-free orders.')
        visible = True
        version = __version__

    def ready(self):
        from . import signals  # NOQA


