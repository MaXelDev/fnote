"""Point d'entrée de Plume : configuration Wayland, QApplication, fenêtre principale."""
from __future__ import annotations

import argparse
import os
import sys


def configure_platform(env=os.environ, x11: bool = False) -> None:
    """Wayland natif, ou X11 via XWayland (x11=True) avec repli sur l'autre.

    Sous GNOME Wayland, le curseur vu pendant l'écriture est celui de la souris, avec la forme
    choisie par la dernière fenêtre survolée : Plume ne peut le cacher que si la souris est
    passée sur lui. Via XWayland, Plume gère lui-même le curseur et il reste caché.
    """
    if "QT_QPA_PLATFORM" not in env and env.get("WAYLAND_DISPLAY"):
        env["QT_QPA_PLATFORM"] = "xcb;wayland" if x11 and env.get("DISPLAY") else "wayland;xcb"


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="plume", description="Prise de notes manuscrites au stylet.")
    p.add_argument("file", nargs="?", help="note .plume à ouvrir")
    p.add_argument("--debug-tablet", action="store_true", help="ouvre la fenêtre de diagnostic du stylet")
    p.add_argument("--debug-perf", action="store_true", help="affiche fps et temps de rendu sur le canevas")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    from .model.config import Config
    config = Config.load()
    configure_platform(x11=config.x11_mode)

    from PySide6.QtCore import QCoreApplication, Qt
    from PySide6.QtWidgets import QApplication

    # Aucun point du stylet ne doit être fusionné ou perdu (fluidité, §5).
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_CompressTabletEvents, False)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_CompressHighFrequencyEvents, False)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Plume")
    app.setDesktopFileName("plume")  # app_id Wayland

    from .view import style
    style.apply(app)

    if args.debug_tablet:
        from .view.debug_tablet import TabletDebugWindow
        window = TabletDebugWindow()
        window.show()
        return app.exec()

    from .controller.input_router import router
    from .view.main_window import MainWindow
    router()  # curseur caché et rejet de la paume, pour toute l'application
    from .controller.tools.lasso import release_clipboard_on_quit
    release_clipboard_on_quit(app)
    window = MainWindow(config, args.file, debug_perf=args.debug_perf)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
