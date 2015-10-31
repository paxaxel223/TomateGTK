from __future__ import unicode_literals

from locale import gettext as _

from gi.repository import AppIndicator3, Gtk
from wiring import implements, inject, Interface, Module, SingletonScope

from tomate.signals import subscribe


class IIndicator(Interface):

    def hide(*args, **kwargs):
        pass

    def show(*args, **kwargs):
        pass

    def set_icon(icon):
        pass


@implements(IIndicator)
class Indicator(object):

    subscriptions = (
        ('session_ended', 'hide'),
        ('view_showed', 'hide'),
        ('view_hid', 'show'),
    )

    @subscribe
    @inject(config='tomate.config', view='tomate.view')
    def __init__(self, config, view):
        self.config = config
        self.view = view

        menuitem = Gtk.MenuItem(_('Show'), visible=False)
        menuitem.connect('activate', self.on_show_menu_activate)
        menu = Gtk.Menu(halign=Gtk.Align.CENTER)
        menu.add(menuitem)

        menu.show_all()

        self.indicator = AppIndicator3.Indicator.new(
                'tomate',
                'tomate-indicator',
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )

        self.indicator.set_icon_theme_path(self.config.get_icon_paths()[0])

        self.indicator.set_menu(menu)

    def on_show_menu_activate(self, widget):
        return self.view.show()

    def show(self, *args, **kwargs):
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    def hide(self, *args, **kwargs):
        self.indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)

    def set_icon(self, icon):
        self.indicator.set_icon(icon)


class IndicatorProvider(Module):
    factories = {
        'tomate.indicator': (Indicator, SingletonScope),
    }