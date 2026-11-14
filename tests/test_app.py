from plume.app import configure_platform, parse_args


def test_wayland_with_xcb_fallback():
    env = {"WAYLAND_DISPLAY": "wayland-0"}
    configure_platform(env)
    assert env["QT_QPA_PLATFORM"] == "wayland;xcb"


def test_user_choice_is_respected():
    env = {"WAYLAND_DISPLAY": "wayland-0", "QT_QPA_PLATFORM": "xcb"}
    configure_platform(env)
    assert env["QT_QPA_PLATFORM"] == "xcb"


def test_no_wayland_leaves_default():
    env = {}
    configure_platform(env)
    assert "QT_QPA_PLATFORM" not in env


def test_args():
    a = parse_args(["note.plume", "--debug-tablet"])
    assert a.file == "note.plume" and a.debug_tablet
