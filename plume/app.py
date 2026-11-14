"""Point d'entrée de Plume : configuration Wayland, QApplication, fenêtre principale."""
from __future__ import annotations

import argparse
import os
import sys


def configure_platform(env=os.environ) -> None:
    """Wayland natif en priorité, repli automatique sur X11 (xcb) si indisponible."""
    if "QT_QPA_PLATFORM" not in env and env.get("WAYLAND_DISPLAY"):
        env["QT_QPA_PLATFORM"] = "wayland;xcb"


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="plume", description="Prise de notes manuscrites au stylet.")
    p.add_argument("file", nargs="?", help="note .plume à ouvrir")
    p.add_argument("--debug-tablet", action="store_true", help="ouvre la fenêtre de diagnostic du stylet")
    p.add_argument("--debug-perf", action="store_true", help="affiche fps et temps de rendu sur le canevas")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    configure_platform()

    from PySide6.QtCore import QCoreApplication, Qt, QTimer
    from PySide6.QtWidgets import QApplication

    # Aucun point du stylet ne doit être fusionné ou perdu (fluidité, §5).
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_CompressTabletEvents, False)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_CompressHighFrequencyEvents, False)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Plume")
    app.setDesktopFileName("plume")  # app_id Wayland

    from .model.config import Config
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
    window = MainWindow(Config.load(), args.file, debug_perf=args.debug_perf)
    window.show()
    QTimer.singleShot(0, window.ensure_vault)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
