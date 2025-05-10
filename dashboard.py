"""service_dashboard.py 

* Groups services and ports under bold section headers
* Emoji indicators (🟢 / 🔴 / ⚠️) + colour bars for instant recognition
* Spacious cards with subtle borders
* Fully centred in the terminal, resizes gracefully

Python 3.10+   ·   pip install textual psutil
"""

from __future__ import annotations

import socket
import psutil
from datetime import datetime
from typing import Tuple

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Static

# ─── WHAT TO MONITOR ─────────────────────────────────────────────────────────
SERVICES = {
    "SQLServer": "MSSQL$MSSQLSERVER01",
}
PORTS = {
    "MongoDB": 27017,
    "Solr":  8983,
    "Redis": 6379,
    "Postgres" : 5432,
    "RabbitMQ": 5672,
    "Redacted1": 9876,
    "Redacted2":5445
}
POLL_SECONDS = 2                    # refresh cadence (s)
BAR_WIDTH    = 38                   # wider pane (chars)
TILE_HEIGHT  = 3                    # lines per tile
# ─────────────────────────────────────────────────────────────────────────────

COLOR_SCHEME: dict[bool | None, Tuple[str, str]] = {
    True:  ("green",  "black"),
    False: ("red",    "white"),
    None:  ("orange", "black"),
}
ICON = {True: "🟢", False: "🔴", None: "⚠️"}

# ─── STATUS HELPERS ──────────────────────────────────────────────────────────

def service_status(name: str) -> bool | None:
    try:
        return psutil.win_service_get(name).status() == "running"
    except Exception:
        return None


def port_status(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


def get_statuses() -> dict[str, bool | None]:
    data: dict[str, bool | None] = {}
    data.update({lbl: service_status(svc) for lbl, svc in SERVICES.items()})
    data.update({lbl: port_status(port)   for lbl, port in PORTS.items()})
    return data

# ─── UI COMPONENTS ───────────────────────────────────────────────────────────
class SectionHeader(Static):
    """Bold title row between groups."""
    def __init__(self, text: str):
        super().__init__(text.upper(), id=f"hdr_{text}")
        self.styles.width = BAR_WIDTH
        self.styles.height = 1
        self.styles.padding = (0, 1)
        self.styles.align_horizontal = "left"
        self.styles.border_bottom = ("heavy", "grey")
        self.styles.color = "white"
        self.styles.background = "black"
        self.styles.bold = True


class Tile(Static):
    """Multi-line status card."""

    status: reactive[bool | None] = reactive(None)

    def __init__(self, label: str):
        super().__init__(label, id=label)
        self.label = label
        self.styles.height = TILE_HEIGHT
        self.styles.width = BAR_WIDTH
        self.styles.padding = (0, 2)
        self.styles.border = ("round", "grey")
        self.styles.align_horizontal = "left"

    def watch_status(self, value: bool | None):  # noqa: D401
        bg, fg = COLOR_SCHEME[value]
        self.styles.background = bg
        self.styles.color = fg
        self.styles.border_color = fg
        self.update(f"{ICON[value]}  {self.label}")


class FooterBar(Static):
    """Aggregated counts & clock."""
    def update_content(self, up: int, down: int, unk: int, ts: str) -> None:
        self.update(
            f"[white on black]🟢 {up}   🔴 {down}   ⚠️ {unk}    {ts}")


class ServiceDash(App):
    TITLE = "Service Dashboard"
    CSS = f"""
    Screen {{
        layout: vertical;
        align-horizontal: center;
        align-vertical: middle;
        background: black;
        padding: 2 4;
    }}

    Tile {{
        width: {BAR_WIDTH};
    }}
    """

    def compose(self) -> ComposeResult:
        self.tiles: dict[str, Tile] = {}

        yield SectionHeader("Services")
        for label in SERVICES.keys():
            tile = Tile(label)
            self.tiles[label] = tile
            yield tile

        yield SectionHeader("Ports")
        for label in PORTS.keys():
            tile = Tile(label)
            self.tiles[label] = tile
            yield tile

        self.footer = FooterBar()
        self.footer.styles.padding = (1, 2)
        yield self.footer

    async def on_mount(self):
        self.refresh_statuses()
        self.set_interval(POLL_SECONDS, self.refresh_statuses)

    def refresh_statuses(self):
        statuses = get_statuses()
        for label, state in statuses.items():
            self.tiles[label].status = state
        up = sum(1 for s in statuses.values() if s)
        down = sum(1 for s in statuses.values() if s is False)
        unk = sum(1 for s in statuses.values() if s is None)
        self.footer.update_content(up, down, unk, datetime.now().strftime("%H:%M:%S"))


if __name__ == "__main__":
    ServiceDash().run()
