import pytest
from gi.repository import Gdk, Gtk
from wiring.scanning import scan_to_graph

from tomate.pomodoro import Events
from tomate.ui import Systray, Window
from tomate.ui.testing import Q, active_shortcut, create_session_payload


@pytest.fixture
def window(bus, config, graph, session) -> Window:
    graph.register_instance("tomate.bus", bus)
    graph.register_instance("tomate.config", config)
    graph.register_instance("tomate.session", session)

    namespaces = [
        "tomate.ui",
        "tomate.pomodoro.plugin",
    ]
    scan_to_graph(namespaces, graph)
    return graph.get("tomate.ui.view")


def test_module(graph, window):
    instance = graph.get("tomate.ui.view")

    assert isinstance(instance, Window)
    assert instance is window


def test_init(session, window):
    session.ready.assert_called_once_with()

    # session button
    assert Q.select(window.widget, Q.props("name", "session.pomodoro"))
    assert Q.select(window.widget, Q.props("name", "session.short_break"))
    assert Q.select(window.widget, Q.props("name", "session.long_break"))

    # headerbar
    assert Q.select(window.widget, Q.props("name", "session.start"))
    assert Q.select(window.widget, Q.props("name", "session.reset"))
    assert Q.select(window.widget, Q.props("name", "session.stop"))

    # countdown
    assert Q.select(window.widget, Q.props("label", "00:00"))


def test_shortcuts(shortcut_engine, window):
    from tomate.ui.widgets import HeaderBar

    assert active_shortcut(shortcut_engine, HeaderBar.START_SHORTCUT, window=window.widget) is True


def test_run(mocker, window):
    gtk_main = mocker.patch("tomate.ui.window.Gtk.main")
    show_all = mocker.patch("tomate.ui.window.Gtk.Window.show_all")

    window.run()

    gtk_main.assert_called_once_with()
    show_all.assert_called_once_with()


class TestWindowHide:
    def test_iconify_when_tray_icon_plugin_is_not_registered(self, window, bus, mocker):
        subscriber = mocker.Mock()
        bus.connect(Events.WINDOW_HIDE, subscriber, weak=False)

        result = window.hide()

        assert result is Gtk.true
        subscriber.assert_called_once_with(Events.WINDOW_HIDE, payload=None)

    def test_deletes_when_tray_icon_plugin_is_registered(self, bus, graph, mocker, window):
        graph.register_factory(Systray, mocker.Mock)
        subscriber = mocker.Mock()
        bus.connect(Events.WINDOW_HIDE, subscriber, weak=False)
        window.widget.set_visible(True)

        result = window.hide()

        assert result
        assert window.widget.get_visible() is False
        subscriber.assert_called_once_with(Events.WINDOW_HIDE, payload=None)


class TestWindowQuit:
    def test_quits_when_timer_is_not_running(self, mocker, session, window):
        main_quit = mocker.patch("tomate.ui.window.Gtk.main_quit")
        session.is_running.return_value = False

        window.widget.emit("delete-event", Gdk.Event.new(Gdk.EventType.DELETE))

        main_quit.assert_called_once_with()

    def test_hides_when_timer_is_running(self, bus, mocker, session, window):
        session.is_running.return_value = True
        subscriber = mocker.Mock()
        bus.connect(Events.WINDOW_HIDE, subscriber, weak=False)

        window.widget.emit("delete-event", Gdk.Event.new(Gdk.EventType.DELETE))

        subscriber.assert_called_once_with(Events.WINDOW_HIDE, payload=None)


def test_shows_window_when_session_end(bus, mocker, window):
    window.widget.props.visible = False
    subscriber = mocker.Mock()
    bus.connect(Events.WINDOW_SHOW, subscriber, weak=False)

    payload = create_session_payload()
    bus.send(Events.SESSION_END, payload=payload)

    assert window.widget.props.visible is True
    subscriber.assert_called_once_with(Events.WINDOW_SHOW, payload=None)
