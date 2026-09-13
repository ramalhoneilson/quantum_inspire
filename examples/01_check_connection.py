#!/usr/bin/env python3
"""Example 1: Check Quantum Inspire connection, credentials, and list backends.

Run this first to verify that your environment is properly authenticated.

Usage:
    python examples/01_check_connection.py
"""

from __future__ import annotations

import sys
from rich.console import Console
from rich.table import Table

from qi_starter.auth import check_auth_status, get_provider
from qi_starter.backend import describe_backends


def main():
    console = Console()
    console.print("\n[bold cyan]=== Quantum Inspire Connection & Account Check ===[/bold cyan]\n")

    # Step 1: Check offline configuration file
    auth_info = check_auth_status()
    if not auth_info["present"]:
        console.print("[bold red]❌ No credentials file found![/bold red]")
        console.print(f"Looked at: {auth_info['path']}")
        console.print("\n[yellow]To log in for the first time:[/yellow]")
        console.print("  Run [bold green]qi login[/bold green] in your terminal.")
        console.print("  This will open a browser window for Quantum Inspire OAuth authentication.\n")
        sys.exit(1)

    console.print(f"✅ Credentials file found at: [green]{auth_info['path']}[/green]")
    console.print(f"   Default Host: [cyan]{auth_info['host']}[/cyan]")
    if auth_info.get("refresh_expires_at"):
        expired = auth_info.get("is_expired", False)
        status_color = "red" if expired else "green"
        status_text = "EXPIRED (run `qi login --force`)" if expired else "Active"
        console.print(f"   Refresh Token Expiry: {auth_info['refresh_expires_at']} [{status_color}]({status_text})[/{status_color}]")

    # Step 2: Test connecting via QIProvider
    console.print("\n[bold]Connecting to Quantum Inspire API...[/bold]")
    try:
        provider = get_provider()
    except Exception as exc:
        console.print(f"[bold red]❌ Failed to connect:[/bold red] {exc}")
        sys.exit(1)

    console.print("✅ Successfully authenticated via QIProvider!\n")

    # Step 3: Discover available backends (emulators and QPUs)
    backends = describe_backends(provider)
    if not backends:
        console.print("[yellow]No backends visible to this account.[/yellow]")
        return

    table = Table(title="Available Quantum Inspire Backends")
    table.add_column("Name", style="bold cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Qubits", justify="right")
    table.add_column("Max Shots", justify="right")
    table.add_column("Max Batch", justify="right")
    table.add_column("Status", style="green")

    for b in backends:
        b_type = "Hardware QPU" if b["is_hardware"] else "Emulator"
        table.add_row(
            b["name"],
            b_type,
            str(b["num_qubits"] or "?"),
            str(b["max_shots"] or "?"),
            str(b["max_jobs_per_batch_job"] or "1"),
            b["status"],
        )

    console.print(table)
    console.print("\n[dim]Note: Backends marked 'Hardware QPU' consume compute quota and require confirmation.[/dim]\n")


if __name__ == "__main__":
    main()
