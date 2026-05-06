#!/usr/bin/env python3
"""
main.py – BAIT AI Assistant Entry Point
========================================
Usage:
  python main.py            → Text mode (type commands)
  python main.py --voice    → Voice mode (speak to BAIT)
  python main.py --wake     → Always-on wake-word mode ("Hey BAIT")
"""

import sys
import argparse
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from bait.brain import BAITBrain
from bait.voice import speak, listen, is_wake_word, strip_wake_word

console = Console()

BANNER = """
██████╗  █████╗ ██╗████████╗
██╔══██╗██╔══██╗██║╚══██╔══╝
██████╔╝███████║██║   ██║   
██╔══██╗██╔══██║██║   ██║   
██████╔╝██║  ██║██║   ██║   
╚═════╝ ╚═╝  ╚═╝╚═╝   ╚═╝  
"""

SPECIAL_COMMANDS = {
    "exit", "quit", "bye", "shutdown",
    "clear memory", "reset", "forget",
    "help", "commands", "what can you do",
}

HELP_TEXT = """
[bold cyan]BAIT Commands:[/bold cyan]
  [green]• Open an app[/green]         → "open chrome", "launch spotify"
  [green]• Google search[/green]       → "search for AI news on google"
  [green]• YouTube search[/green]      → "search lofi music on youtube"
  [green]• Open a website[/green]      → "open github.com"
  [green]• Volume control[/green]      → "set volume to 50" / "what's the volume"
  [green]• Screenshot[/green]          → "take a screenshot"
  [green]• Battery[/green]             → "check battery"
  [green]• Wi-Fi[/green]              → "what wifi am I on"
  [green]• System info[/green]         → "system info"
  [green]• List apps[/green]           → "what apps are open"
  [green]• Close app[/green]           → "close chrome"
  [green]• Time[/green]                → "what time is it"
  [green]• Chat[/green]                → Just talk — BAIT will respond

  [yellow]clear memory[/yellow]        → Wipe conversation history
  [yellow]exit / quit / bye[/yellow]   → Shutdown BAIT
"""


def print_banner():
    console.print(f"[bold cyan]{BANNER}[/bold cyan]")
    console.print(Panel.fit(
        "[bold white]Your Personal AI Assistant — macOS Edition[/bold white]\n"
        "[dim]Powered by Groq · Gemini · ElevenLabs · 11 Mac Tools[/dim]",
        border_style="cyan",
        box=box.DOUBLE_EDGE,
    ))
    console.print()


def print_user(text: str):
    console.print(f"\n[bold green]You[/bold green] → {text}")


def print_bait(text: str):
    console.print(f"\n[bold cyan]BAIT[/bold cyan] → {text}\n")


def handle_special(command: str, brain: BAITBrain) -> bool:
    """Handle built-in special commands. Returns True if handled."""
    cmd = command.lower().strip().rstrip(".")

    if cmd in ("exit", "quit", "bye", "shutdown"):
        farewell = "Shutting down. Stay sharp, Boss."
        print_bait(farewell)
        speak(farewell)
        sys.exit(0)

    if cmd in ("clear memory", "reset", "forget"):
        reply = brain.reset_memory()
        print_bait(reply)
        speak(reply)
        return True

    if cmd in ("help", "commands", "what can you do"):
        console.print(Panel(HELP_TEXT, title="[bold cyan]BAIT Help[/bold cyan]", border_style="cyan"))
        return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# MODES
# ─────────────────────────────────────────────────────────────────────────────

def run_text_mode(brain: BAITBrain):
    """Standard text input loop."""
    console.print("[dim]Text mode active. Type your command or question.[/dim]\n")
    while True:
        try:
            user_input = console.input("[bold green]You[/bold green] → ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if handle_special(user_input, brain):
            continue

        console.print("[dim]Thinking...[/dim]")
        reply = brain.think(user_input)
        print_bait(reply)


def run_voice_mode(brain: BAITBrain):
    """Single-turn voice mode: listen → process → speak."""
    console.print("[dim]Voice mode active. Speak your command after the prompt.[/dim]\n")
    while True:
        console.print("[bold yellow]🎙  Listening...[/bold yellow]")
        text = listen(timeout=8)

        if text is None:
            console.print("[dim]Didn't catch that. Try again.[/dim]")
            continue

        print_user(text)

        if handle_special(text, brain):
            continue

        console.print("[dim]Thinking...[/dim]")
        reply = brain.think(text)
        print_bait(reply)
        speak(reply)


def run_wake_mode(brain: BAITBrain):
    """
    Always-on wake-word mode.
    Continuously listens for "Hey BAIT" then processes the command.
    """
    console.print(
        Panel(
            "[bold]Always-on mode active.[/bold]\n"
            "Say [cyan]\"Hey BAIT\"[/cyan] to activate, then give your command.",
            border_style="yellow",
        )
    )

    greeting = "BAIT online. Say 'Hey BAIT' to wake me up, Boss."
    print_bait(greeting)
    speak(greeting)

    while True:
        # Phase 1: Passive listen for wake word
        console.print("[dim]👂 Waiting for wake word...[/dim]", end="\r")
        raw = listen(timeout=30, phrase_limit=5)

        if raw is None:
            continue

        if not is_wake_word(raw):
            continue  # Not a wake word, keep waiting

        # Phase 2: Wake word detected — listen for the actual command
        ack = "Yes, Boss?"
        print_bait(ack)
        speak(ack, blocking=False)  # Non-blocking so mic stays ready

        console.print("[bold yellow]🎙  Listening for command...[/bold yellow]")
        command = listen(timeout=10, phrase_limit=15)

        if command is None:
            no_cmd = "I didn't catch that. Try again."
            print_bait(no_cmd)
            speak(no_cmd)
            continue

        command = strip_wake_word(command)
        print_user(command)

        if not command:
            continue

        if handle_special(command, brain):
            continue

        console.print("[dim]Thinking...[/dim]")
        reply = brain.think(command)
        print_bait(reply)
        speak(reply)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BAIT – Your Personal AI Assistant for macOS"
    )
    parser.add_argument("--voice", action="store_true", help="Enable voice input mode")
    parser.add_argument("--wake",  action="store_true", help="Enable always-on wake-word mode")
    args = parser.parse_args()

    print_banner()
    brain = BAITBrain()

    # Startup greeting
    greeting = "BAIT online. How can I help you today, Boss?"
    print_bait(greeting)
    if args.voice or args.wake:
        speak(greeting)

    if args.wake:
        run_wake_mode(brain)
    elif args.voice:
        run_voice_mode(brain)
    else:
        run_text_mode(brain)


if __name__ == "__main__":
    main()
