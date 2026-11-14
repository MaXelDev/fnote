"""Garde-fou : Plume est 100 % hors ligne. Échoue si un module réseau est importé."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "plume"

FORBIDDEN = {
    "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "poplib", "imaplib", "telnetlib",
    "xmlrpc", "socketserver", "asyncio.streams", "webbrowser",
    "requests", "httpx", "aiohttp", "urllib3", "websocket", "websockets", "grpc", "paramiko",
}
FORBIDDEN_QT = ("QtNetwork", "QtWebEngine", "QtWebSockets", "QtWebChannel", "QtWebView", "QtHttpServer")


def _bad(module: str) -> bool:
    parts = module.split(".")
    if any(".".join(parts[:i]) in FORBIDDEN for i in range(1, len(parts) + 1)):
        return True
    return any(p.startswith(FORBIDDEN_QT) for p in parts)


def find_network_imports(root: Path = ROOT) -> list[str]:
    found = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                names = [base] + [f"{base}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__" and node.args \
                    and isinstance(node.args[0], ast.Constant):
                names = [str(node.args[0].value)]
            else:
                continue
            bad = [n for n in names if _bad(n)]
            if bad:
                found.append(f"{path.relative_to(root.parent)}:{node.lineno} {bad[0]}")
    return found


def test_no_network_imports():
    assert find_network_imports() == []


def test_detector_catches_forbidden(tmp_path):
    (tmp_path / "x.py").write_text(
        "import requests\nfrom urllib.request import urlopen\nfrom PySide6 import QtNetwork\n"
        "from PySide6.QtNetwork import QTcpSocket\n__import__('socket')\nimport json\n")
    assert len(find_network_imports(tmp_path)) == 5
