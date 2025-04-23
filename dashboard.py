"""service_dashboard.py
Real-time terminal dashboard for Windows services and TCP ports.
Green = running/up, red = stopped/down, yellow = unknown/not installed.
Python 3.10+, requires `pip install textual psutil`.
"""

from __future__ import annotations
import socket
import psutil
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Static, Header, Footer

# ─── EDIT THESE LISTS TO MATCH YOUR ENVIRONMENT ──────────────────────────────
SERVICES = {
    "SQLServer": "MSSQL$MSSQLSERVER01",  # display label : service name
    "MongoDB": "MongoDB",
}

PORTS = {
    "Solr": 8983,           # display label : tcp port
    "Redis": 6379
}

POLL_SECONDS = 2                    # refresh cadence in seconds
# ─────────────────────────────────────────────────────────────────────────────

def service_status(name: str) -> bool | None:
    """Return True (running), False (stopped), or None (service absent)."""
    try:
        return psutil.win_service_get(name).status() == "running"
    except Exception:
        return None


def port_status(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if TCP connect succeeds, False otherwise."""
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


def get_statuses() -> dict[str, bool | None]:
    """Collect a dict mapping labels to status booleans / None."""
    data: dict[str, bool | None] = {}
    for label, svc in SERVICES.items():
        data[label] = service_status(svc)
    for label, port in PORTS.items():
        data[label] = port_status(port)
    return data


class Tile(Static):
    """Little colored box that flips between UP / DOWN / UNKNOWN."""

    status: reactive[bool | None] = reactive(None)

    def __init__(self, label: str) -> None:
        super().__init__(label, id=label)  # id so we can query later
        self.label = label

    def watch_status(self, value: bool | None) -> None:
        palette = {True: "green", False: "red", None: "yellow"}
        text = {True: "UP", False: "DOWN", None: "UNKNOWN"}[value]
        color = palette[value]
        self.update(f"[b]{self.label}[/b]\n[{color}]{text}[/{color}]")


class ServiceDash(App):
    """Main Textual application."""

    TITLE = "Service Dashboard"
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3;
        grid-gutter: 1;
        padding: 1;
    }
    Tile {
        height: 5;
        width: 25;
        content-align: center middle;
        border: round $accent;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        self.tiles: dict[str, Tile] = {}
        for label in [*SERVICES.keys(), *PORTS.keys()]:
            tile = Tile(label)
            self.tiles[label] = tile
            yield tile
        yield Footer()

    async def on_mount(self) -> None:
        # First update immediately, then every POLL_SECONDS seconds.
        self.refresh_statuses()
        self.set_interval(POLL_SECONDS, self.refresh_statuses)

    def refresh_statuses(self) -> None:
        for label, status in get_statuses().items():
            self.tiles[label].status = status


if __name__ == "__main__":
    ServiceDash().run()
