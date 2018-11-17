import locale
import logging
from locale import gettext as _

from gi.repository import GdkPixbuf, Gtk, Pango
from wiring import inject, SingletonScope
from wiring.scanning import register

locale.textdomain("tomate")
logger = logging.getLogger(__name__)


@register.factory("view.preference", scope=SingletonScope)
class PreferenceDialog(Gtk.Dialog):
    @inject(duration="view.preference.duration", extension="view.preference.extension")
    def __init__(self, duration, extension):
        self.extension = extension
        self.duration = duration

        Gtk.Dialog.__init__(
            self,
            title=_("Preferences"),
            border_width=11,
            modal=True,
            resizable=False,
            window_position=Gtk.WindowPosition.CENTER_ON_PARENT,
        )
        self.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        self.connect("response", lambda widget, response: widget.hide())
        self.set_size_request(350, -1)

        stack = Gtk.Stack()
        stack.add_titled(self.duration.widget, "timer", _("Timer"))

        stack.add_titled(self.extension.widget, "extension", _("Extensions"))

        switcher = Gtk.StackSwitcher(halign=Gtk.Align.CENTER)
        switcher.set_stack(stack)

        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_bottom=12
        )
        vbox.pack_start(switcher, False, False, 0)
        vbox.pack_start(stack, False, False, 0)
        vbox.show_all()

        stack.get_child_by_name("timer").activate()

        self.get_content_area().add(vbox)

    @property
    def widget(self):
        return self

    def refresh_plugins(self):
        self.extension.refresh()


@register.factory("view.preference.duration", scope=SingletonScope)
class TimerTab(Gtk.Grid):
    @inject(config="tomate.config")
    def __init__(self, config):
        self.config = config

        Gtk.Grid.__init__(self, column_spacing=12, row_spacing=6)

        section = self._add_section(_("Duration"))
        self.attach(section, 0, 0, 1, 1)

        # Pomodoro Duration
        label, setting = self._add_setting(
            _("Pomodoro"), Gtk.SpinButton.new_with_range(1, 99, 1), "pomodoro_duration"
        )
        self.attach(label, 0, 1, 1, 1)
        self.attach_next_to(setting, label, Gtk.PositionType.RIGHT, 3, 1)

        # Short Break Duration
        label, setting = self._add_setting(
            _("Short break"),
            Gtk.SpinButton.new_with_range(1, 99, 1),
            "shortbreak_duration",
        )
        self.attach(label, 0, 2, 1, 1)
        self.attach_next_to(setting, label, Gtk.PositionType.RIGHT, 3, 1)

        # Long Break Duration
        label, setting = self._add_setting(
            _("Long Break"),
            Gtk.SpinButton.new_with_range(1, 99, 1),
            "longbreak_duration",
        )
        self.attach(label, 0, 3, 1, 1)
        self.attach_next_to(setting, label, Gtk.PositionType.RIGHT, 3, 1)

    @staticmethod
    def _add_section(name):
        section = Gtk.Label.new()
        section.set_markup("<b>{0}</b>".format(name))
        section.set_halign(Gtk.Align.START)
        return section

    def _add_setting(self, label_name, spinbutton, option):
        label = Gtk.Label.new(label_name + ":")
        label.set_properties(margin_left=12, hexpand=True, halign=Gtk.Align.END)

        spinbutton.set_hexpand(True)
        spinbutton.set_halign(Gtk.Align.START)
        spinbutton.set_value(self.config.get_int("Timer", option))
        spinbutton.connect("value-changed", self._on_spinbutton_value_changed, option)

        setattr(self, option, spinbutton)

        return label, spinbutton

    def _on_spinbutton_value_changed(self, widget, option):
        value = str(widget.get_value_as_int())
        self.config.set("Timer", option, value)

    @property
    def widget(self):
        return self


@register.factory("view.preference.extension", scope=SingletonScope)
class ExtensionTab(Gtk.Box):
    @inject(plugin="tomate.plugin", config="tomate.config", lazy_proxy="tomate.proxy")
    def __init__(self, plugin, config, lazy_proxy):
        self.plugin_manager = plugin
        self.config = config
        self.preference_dialog = lazy_proxy("view.preference")

        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self._store = Gtk.ListStore(
            bool, GdkPixbuf.Pixbuf, str, str, object  # active  # icon  # name  # detail
        )  # plugin

        self.tree_view = Gtk.TreeView(headers_visible=False, model=self._store)
        self.tree_view.get_selection().connect("changed", self._on_tree_view_changed)
        self.tree_view.get_selection().set_mode(Gtk.SelectionMode.BROWSE)

        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", self._on_plugin_toggled)
        column = Gtk.TreeViewColumn("Active", renderer, active=0)
        self.tree_view.append_column(column)

        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn("Icon", renderer, pixbuf=1)
        self.tree_view.append_column(column)

        renderer = Gtk.CellRendererText(wrap_mode=Pango.WrapMode.WORD, wrap_width=200)
        column = Gtk.TreeViewColumn("Detail", renderer, markup=3)
        self.tree_view.append_column(column)

        self.plugin_settings_button = Gtk.Button.new_from_icon_name(
            Gtk.STOCK_PREFERENCES, Gtk.IconSize.MENU
        )
        self.plugin_settings_button.set_sensitive(False)
        self.plugin_settings_button.connect("clicked", self._on_plugin_settings_clicked)

        scrolledwindow = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        scrolledwindow.add(self.tree_view)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.pack_end(self.plugin_settings_button, False, False, 0)

        self.pack_start(scrolledwindow, True, True, 0)
        self.pack_start(hbox, False, False, 0)

        self.show_all()

    @property
    def widget(self):
        return self

    def refresh(self):
        self._clear()

        for plugin in self.plugin_manager.getAllPlugins():
            self._add_plugin(plugin)

        if self._there_are_plugins:
            self._select_first_plugin()

    def _on_tree_view_changed(self, selection):
        _, treeiter = selection.get_selected()

        if treeiter is not None:
            plugin = self.get_selected_plugin()

            if getattr(plugin.plugin_object, "has_settings", False) is True:
                self.plugin_settings_button.set_sensitive(True)
            else:
                self.plugin_settings_button.set_sensitive(False)

    def get_selected_plugin(self):
        _, treeiter = self.tree_view.get_selection().get_selected()

        grid_plugin = GridPlugin.from_iter(self._store, treeiter)

        return self.plugin_manager.getPluginByName(grid_plugin.name)

    @property
    def _toplevel(self):
        return self.preference_dialog.widget

    def _on_plugin_toggled(self, _, path):
        grid_plugin = GridPlugin.from_path(self._store, path)
        grid_plugin.toggle()

        if grid_plugin.is_enable:
            self._activate_plugin(grid_plugin.name)

        else:
            self._deactivate_plugin(grid_plugin.name)

    def _on_plugin_settings_clicked(self, _):
        plugin = self.get_selected_plugin()

        widget = plugin.plugin_object.settings_window()
        widget.set_transient_for(self._toplevel)
        widget.run()

    def _deactivate_plugin(self, plugin_name):
        self.plugin_manager.deactivatePluginByName(plugin_name)
        self.plugin_settings_button.set_sensitive(False)

    def _activate_plugin(self, plugin_name):
        self.plugin_manager.activatePluginByName(plugin_name)

    def _clear(self):
        self._store.clear()

    def _select_first_plugin(self):
        self.tree_view.get_selection().select_iter(self._store.get_iter_first())

    @property
    def _there_are_plugins(self):
        return bool(len(self._store))

    def _add_plugin(self, plugin):
        iconname = getattr(plugin, "icon", "tomate-plugin")
        iconpath = self.config.get_icon_path(iconname, 16)

        self._store.append(
            (
                plugin.plugin_object.is_activated,
                GridPlugin.pixbuf(iconpath),
                plugin.name,
                GridPlugin.markup(plugin),
                plugin,
            )
        )

        logger.debug("component=preference action=addPlugin pluginName=%s", plugin.name)


class GridPlugin(object):
    ACTIVE = 0
    TITLE = 2

    def __init__(self, value):
        self._value = value

    @staticmethod
    def from_iter(treestore, treeiter):
        return GridPlugin(treestore[treeiter])

    @staticmethod
    def from_path(treestore, treepath):
        treeiter = treestore.get_iter(treepath)
        return GridPlugin(treestore[treeiter])

    @property
    def name(self):
        return self._value[self.TITLE]

    @property
    def is_enable(self):
        return self._value[self.ACTIVE]

    def toggle(self):
        self._value[self.ACTIVE] = not self._value[self.ACTIVE]

    @staticmethod
    def pixbuf(icon_path):
        return GdkPixbuf.Pixbuf.new_from_file(icon_path)

    @staticmethod
    def markup(plugin):
        return "<b>{name}</b> ({version})" "\n<small>{description}</small>".format(
            name=plugin.name, version=plugin.version, description=plugin.description
        )
