"""CLI gateway: the zero-setup way to talk to your Waku.

A gateway only moves text in and out; everything interesting happens in the
loop. The CLI streams gate diagnostics and assistant text live, then prints the
final response after the turn completes.
"""

from __future__ import annotations

import sqlite3

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from waku.app import Waku

console = Console()
_stream_state = {"gate_started": False, "reply_started": False}


def _flush() -> None:
    console.file.flush()


def _memory_snapshot(conn: sqlite3.Connection) -> str:
    """Render a bounded, read-only view of Waku's local memory."""
    fact_count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    facts = conn.execute("SELECT subject, content FROM facts ORDER BY id DESC LIMIT 8").fetchall()
    episode_count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    episodes = conn.execute(
        "SELECT happened_at, summary FROM episodes ORDER BY happened_at DESC, id DESC LIMIT 5"
    ).fetchall()
    pending = conn.execute("SELECT COUNT(*) FROM chat_log WHERE consolidated = 0").fetchone()[0]

    lines = [f"Semantic facts ({fact_count})"]
    lines.extend(f"- [{row['subject']}] {row['content']}" for row in facts)
    if not facts:
        lines.append("- none yet")

    lines.extend(["", f"Recent episodes ({episode_count})"])
    lines.extend(f"- {row['happened_at']} - {row['summary']}" for row in episodes)
    if not episodes:
        lines.append("- none yet")

    lines.extend(["", f"Unconsolidated chat messages: {pending}"])
    return "\n".join(lines)


def _reset_stream_state() -> None:
    _stream_state["gate_started"] = False
    _stream_state["reply_started"] = False


def _finish_live_line() -> None:
    if _stream_state["gate_started"] or _stream_state["reply_started"]:
        console.print()
    _reset_stream_state()


def _observer(kind: str, event: dict) -> None:
    """Show the loop's internals live."""
    if kind == "gate_text":
        if not _stream_state["gate_started"]:
            console.print("  [dim]gate raw - [/dim]", end="")
            _stream_state["gate_started"] = True
        console.print(Text(event.get("delta", ""), style="dim"), end="")
        _flush()
    elif kind == "text":
        if not _stream_state["reply_started"]:
            if _stream_state["gate_started"]:
                console.print()
                _stream_state["gate_started"] = False
            console.print("[bold green]waku >[/bold green] ", end="")
            _stream_state["reply_started"] = True
        console.print(Text(event.get("delta", "")), end="")
        _flush()
    elif kind == "stream_fallback":
        _finish_live_line()
        console.print(f"  [dim]stream fallback - {event.get('reason', '')}[/dim]")
    elif kind == "tool":
        _finish_live_line()
        console.print(
            f"  [dim]tool - {event['tool']}({event['args']}) -> "
            f"{event['output'][:80]}[/dim]"
        )
    elif kind == "gate":
        _finish_live_line()
        console.print(f"  [dim]gate - {event['decision']} - {event.get('reason', '')}[/dim]")
    elif kind == "consolidation":
        _finish_live_line()
        console.print(
            f"  [dim]memory - consolidated {event['new_facts']} fact(s) "
            "from recent chats[/dim]"
        )


def main() -> None:
    waku = Waku()
    waku.session.session_id = "terminal"
    console.print(Panel.fit(
        "[bold]Waku[/bold] - local, yours, transparent.\n"
        f"home: {waku.settings.home.resolve()}   model: {waku.settings.model}\n"
        "Commands: /memory - /quit",
        border_style="cyan",
    ))
    while True:
        try:
            user_message = console.input("[bold cyan]you >[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_message:
            continue
        if user_message in ("/quit", "/exit"):
            break
        if user_message == "/memory":
            console.print(
                Panel(
                    Text(_memory_snapshot(waku.conn)),
                    title="Memory snapshot",
                    border_style="cyan",
                )
            )
            continue
        _reset_stream_state()
        result = waku.respond(user_message, observer=_observer, source="cli", stream=True)
        _finish_live_line()
        console.print(f"[bold green]waku final >[/bold green] {result.reply}\n")
    console.print("[dim]bye - your memory stays in state.db[/dim]")


if __name__ == "__main__":
    main()
