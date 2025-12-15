"""
Dashboard semplice per il monitoraggio dell'Auditor Agent.
Mostra statistiche in tempo reale e stato del sistema.
"""

import time
import threading
from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text


class MonitoringDashboard:
    """Dashboard di monitoraggio per l'Auditor Agent."""

    def __init__(self, config):
        """Inizializza la dashboard."""
        self.config = config
        self.console = Console()
        self.live = None
        self.running = False
        self.stats = {
            'events_processed': 0,
            'issues_found': 0,
            'warnings_sent': 0,
            'blocks_applied': 0,
            'uptime_seconds': 0,
            'last_event_time': None,
            'active_instances': 0
        }
        self.thread = None

    def start(self):
        """Avvia la dashboard."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._dashboard_loop, daemon=True)
        self.thread.start()

        print("📊 Dashboard di monitoraggio avviata")
        print("Premi Ctrl+C per interrompere")

    def update(self):
        """
        Compatibilità con AuditorAgent: attualmente la dashboard aggiorna in autonomia nel thread.
        Questo metodo è un NO-OP intenzionale.
        """
        return

    def stop(self):
        """Ferma la dashboard."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("📊 Dashboard fermata")

    def update_stats(self, new_stats: Dict[str, Any]):
        """Aggiorna le statistiche."""
        self.stats.update(new_stats)
        self.stats['last_event_time'] = time.time()

    def _dashboard_loop(self):
        """Loop principale della dashboard."""
        start_time = time.time()

        with Live(console=self.console, refresh_per_second=2) as live:
            while self.running:
                # Aggiorna uptime
                self.stats['uptime_seconds'] = int(time.time() - start_time)

                # Crea il display
                display = self._create_display()

                # Aggiorna live display
                live.update(display)

                # Pausa
                time.sleep(0.5)

    def _create_display(self) -> Panel:
        """Crea il pannello principale della dashboard."""
        # Header
        header = Text("🤖 Auditor Agent Dashboard", style="bold blue")
        header.append(f"\n🟢 Attivo - Uptime: {self._format_uptime()}", style="green")

        # Statistiche principali
        main_stats = self._create_main_stats_table()

        # Stato sistema
        system_status = self._create_system_status()

        # Log recenti (placeholder)
        recent_activity = self._create_recent_activity()

        # Combina tutto
        content = f"{header}\n\n{main_stats}\n\n{system_status}\n\n{recent_activity}"

        return Panel(
            content,
            title="[bold]Auditor Agent Monitor[/bold]",
            border_style="blue",
            padding=(1, 2)
        )

    def _create_main_stats_table(self) -> Table:
        """Crea tabella statistiche principali."""
        table = Table(title="📈 Statistiche Principali")
        table.add_column("Metrica", style="cyan")
        table.add_column("Valore", style="magenta", justify="right")
        table.add_column("Stato", style="green")

        stats_data = [
            ("Eventi Processati", self.stats['events_processed'], "📥"),
            ("Problemi Rilevati", self.stats['issues_found'], "🔍"),
            ("Avvisi Inviati", self.stats['warnings_sent'], "⚠️"),
            ("Blocchi Applicati", self.stats['blocks_applied'], "🚫"),
            ("Istanze Attive", self.stats['active_instances'], "👥"),
        ]

        for metric, value, icon in stats_data:
            status = "🟢" if value > 0 else "⚪"
            table.add_row(f"{icon} {metric}", str(value), status)

        return table

    def _create_system_status(self) -> Panel:
        """Crea pannello stato sistema."""
        last_event = "Mai" if not self.stats['last_event_time'] else \
                    self._format_time_ago(self.stats['last_event_time'])

        status_lines = [
            f"🕐 Ultimo Evento: {last_event}",
            f"⚙️  Modalità: {self.config.mode.upper()}",
            f"🎯 Target: {self.config.target_instance or 'Tutte le istanze'}",
            f"🔧 Rules file: {getattr(self.config, 'rules_path', 'N/A')}"
        ]

        return Panel(
            "\n".join(status_lines),
            title="🔧 Stato Sistema",
            border_style="yellow"
        )

    def _create_recent_activity(self) -> Panel:
        """Crea pannello attività recente."""
        # Placeholder per attività recente
        activities = [
            "🔍 In attesa di eventi...",
            "⚡ Sistema pronto",
            "📊 Monitoraggio attivo"
        ]

        return Panel(
            "\n".join(f"• {activity}" for activity in activities),
            title="📋 Attività Recente",
            border_style="green"
        )

    def _format_uptime(self) -> str:
        """Formatta l'uptime in modo leggibile."""
        seconds = self.stats['uptime_seconds']
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def _format_time_ago(self, timestamp: float) -> str:
        """Formatta il tempo trascorso."""
        seconds_ago = int(time.time() - timestamp)

        if seconds_ago < 60:
            return f"{seconds_ago}s fa"
        elif seconds_ago < 3600:
            return f"{seconds_ago // 60}m fa"
        else:
            return f"{seconds_ago // 3600}h fa"

    def log_event(self, event_type: str, description: str, severity: str = "info"):
        """Logga un evento nella dashboard."""
        # Qui potremmo aggiungere una coda di eventi recenti
        # Per ora, solo aggiorna le statistiche se necessario
        if severity in ['warning', 'error', 'high']:
            self.stats['issues_found'] += 1
