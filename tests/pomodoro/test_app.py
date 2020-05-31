import contextlib

import dbus
import pytest

from tomate.pomodoro import State


@pytest.fixture()
def subject(mocker, mock_view, mock_plugin):
    from tomate.pomodoro.app import Application

    return Application(bus=mocker.Mock(), view=mock_view, plugin=mock_plugin)


def test_from_graph(mocker, graph, mock_plugin, mock_view):
    mocker.patch("tomate.pomodoro.app.dbus.SessionBus")

    from tomate.pomodoro.app import Application

    graph.register_instance("tomate.ui.view", mock_view)
    graph.register_instance("tomate.plugin", mock_plugin)
    graph.register_factory("tomate.app", Application)

    app = Application.from_graph(graph)

    assert isinstance(app, Application)

    with contextlib.ExitStack() as stack:
        stack.enter_context(mocker.patch(
            "tomate.pomodoro.app.dbus.SessionBus.return_value.request_name",
            return_value=dbus.bus.REQUEST_NAME_REPLY_EXISTS,
        ))
        dbus_app = Application.from_graph(graph)

        assert isinstance(dbus_app, dbus.Interface)


def test_run_when_not_running(subject):
    subject.Run()

    subject.window.run.assert_called_once_with()


def test_run_when_already_running(subject):
    subject.state = State.started

    subject.Run()

    subject.window.show.assert_called_once_with()


def test_is_running(subject):
    assert not subject.IsRunning()

    subject.state = State.started

    assert subject.IsRunning()


def test_load_plugins_in_init(subject, mock_plugin):
    mock_plugin.collectPlugins()
