"""service_dashboard.py  ─ Centered, spacious status pane

A clean, centred column that shows service / port health with generous
spacing and subtle borders.

Colours:  green = up, red = down, amber = unknown.
Python 3.10+,  `pip install textual psutil`.
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
    "SQL":   "MSSQL$MSSQLSERVER01",
    "Mongo": "MongoDB",
}
PORTS = {
    "Solr":  8983,
    "Redis": 6379,
    "WebAPI":   9876,
}
POLL_SECONDS = 2                    # refresh cadence (s)
BAR_WIDTH    = 32                   # generous width (chars)
TILE_HEIGHT  = 3                    # lines per tile
# ─────────────────────────────────────────────────────────────────────────────

COLOR_SCHEME: dict[bool | None, Tuple[str, str]] = {
    True:  ("green",  "black"),  # running
    False: ("red",     "white"),  # stopped
    None:  ("orange", "black"),  # unknown / absent
}
ICON = {True: "✔", False: "✖", None: "…"}

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
class Tile(Static):
    """Multi-line status card."""

    status: reactive[bool | None] = reactive(None)

    def __init__(self, label: str) -> None:
        super().__init__(label, id=label)
        self.label = label
        self.styles.height = TILE_HEIGHT
        self.styles.width = BAR_WIDTH
        self.styles.padding = (0, 2)
        self.styles.border = ("round", "black")
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
            f"[white on black]\u2714 {up}   \u2716 {down}   … {unk}    {ts}")
        # ✔ and ✖ glyphs shown via codepoints for uniformity


class ServiceDash(App):
    TITLE = "Service Status"
    CSS = f"""
    Screen {{
        layout: vertical;
        align-horizontal: center;  /* centre column horizontally */
        align-vertical: middle;    /* centre column vertically */
        background: black;
        padding: 2 4;             /* generous breathing room */
    }}

    Tile {{  /* override defaults */
        width: {BAR_WIDTH};
    }}
    """

    def compose(self) -> ComposeResult:
        self.tiles: dict[str, Tile] = {}
        for label in [*SERVICES.keys(), *PORTS.keys()]:
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
        up   = sum(1 for s in statuses.values() if s)
        down = sum(1 for s in statuses.values() if s is False)
        unk  = sum(1 for s in statuses.values() if s is None)
        self.footer.update_content(up, down, unk, datetime.now().strftime("%H:%M:%S"))


if __name__ == "__main__":
    ServiceDash().run()
