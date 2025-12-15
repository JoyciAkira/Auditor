#!/usr/bin/env python3
"""
Auditor Agent - Claude Code Companion
Main entry point per l'agente di auditing che monitora Claude Code in tempo reale.
"""

import sys
import time
import signal
import argparse
from pathlib import Path
from typing import Optional

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent.parent))

from communication_layer.hcom_client import HComClient
from audit_engine.auditor import AuditorEngine, AuditResult
from monitoring.dashboard import MonitoringDashboard
from config.agent_config import AgentConfig


class AuditorAgent:
    """Agente principale di auditing per Claude Code."""

    def __init__(self, config_path: Optional[str] = None):
        """Inizializza l'agente auditor."""
        self.config = AgentConfig(config_path)
        self.hcom_client = HComClient(self.config)
        self.audit_engine = AuditorEngine(self.config)
        self.dashboard = MonitoringDashboard(self.config)
        self.running = False

    def start(self):
        """Avvia l'agente auditor."""
        print("🚀 Avvio Auditor Agent...")
        print(f"📊 Modalità: {self.config.mode}")
        print(f"🎯 Target: {self.config.target_instance or 'tutte le istanze'}")

        try:
            # Connetti al sistema hcom
            self.hcom_client.connect()

            # Avvia il motore di auditing
            self.audit_engine.start()

            # Avvia dashboard se richiesta
            if self.config.enable_dashboard:
                self.dashboard.start()

            self.running = True
            print("✅ Auditor Agent attivo e operativo")

            # Loop principale
            self._main_loop()

        except KeyboardInterrupt:
            print("\n⏹️  Arresto Auditor Agent...")
            self.stop()
        except Exception as e:
            print(f"❌ Errore durante l'avvio: {e}")
            self.stop()
            sys.exit(1)

    def stop(self):
        """Ferma l'agente auditor."""
        self.running = False

        if self.dashboard:
            self.dashboard.stop()

        if self.audit_engine:
            self.audit_engine.stop()

        if self.hcom_client:
            self.hcom_client.disconnect()

        print("👋 Auditor Agent fermato")

    def _main_loop(self):
        """Loop principale di monitoraggio."""
        while self.running:
            try:
                # Controlla nuovi eventi
                events = self.hcom_client.get_new_events()

                if events:
                    for event in events:
                        self._process_event(event)

                # Aggiorna dashboard
                if self.dashboard:
                    self.dashboard.update()

                # Pausa breve
                time.sleep(0.1)

            except Exception as e:
                print(f"⚠️  Errore nel loop principale: {e}")
                time.sleep(1)

    def _process_event(self, event: dict):
        """Elabora un evento ricevuto."""
        # Filtra per istanza target se configurata.
        instance = event.get("instance") or event.get("data", {}).get("instance")
        if self.config.target_instance and instance and instance != self.config.target_instance:
            return

        event_type = event.get('type', 'unknown')

        # Log dell'evento
        print(f"📥 Evento ricevuto: {event_type}")

        # Inoltra al motore di auditing
        audit_result = self.audit_engine.analyze_event(event)

        if audit_result:
            # Gestisci il risultato dell'audit
            self._handle_audit_result(audit_result, event)

    def _handle_audit_result(self, result: AuditResult, original_event: dict):
        """Gestisce il risultato di un'analisi di audit."""
        severity = result.severity
        action = result.action

        # Log del risultato
        print(f"🔍 Audit result: {severity} - {action}")

        # Aggiorna stats e dashboard
        if self.dashboard:
            self.dashboard.update_stats(self.audit_engine.stats)

        if action == 'block' and self.config.mode == 'block':
            # Blocca l'azione
            self._block_action(original_event, result)
        elif action == 'warn' or (action == 'block' and self.config.mode == 'warn'):
            # Invia avviso
            self._send_warning(result)
        elif action == 'suggest':
            # Invia suggerimento
            self._send_suggestion(result)

    def _block_action(self, original_event: dict, result: AuditResult):
        """
        Implementazione MINIMA del blocco.
        Limite: non “interrompe” realmente un tool già eseguito; invia un messaggio di stop/attenzione.
        Un blocco hard richiede gate su hook Stop / PreToolUse o git hooks (non implementato qui).
        """
        target = self.config.target_instance or original_event.get("instance")
        reason = f"{result.rule_name}: {result.description}"
        if target:
            self.hcom_client.block_instance_action(str(target), reason)
        else:
            # fallback broadcast
            self.hcom_client.send_message(f"🚫 AUDIT BLOCK: {reason}", intent="error")

    def _send_warning(self, result: AuditResult):
        target = self.config.target_instance
        msg = f"{result.rule_name}: {result.description}"
        if result.suggestion:
            msg += f" | suggestion: {result.suggestion}"
        if target:
            self.hcom_client.warn_instance(target, msg)
        else:
            self.hcom_client.send_message(f"⚠️ AUDIT WARNING: {msg}", intent="inform")

    def _send_suggestion(self, result: AuditResult):
        msg = f"{result.rule_name}: {result.description}"
        if result.suggestion:
            msg += f" | suggestion: {result.suggestion}"
        self.hcom_client.send_message(f"💡 AUDIT SUGGESTION: {msg}", intent="inform")


def main():
    """Funzione principale."""
    parser = argparse.ArgumentParser(description="Auditor Agent - Claude Code Companion")
    parser.add_argument('--config', '-c', help='Path al file di configurazione')
    parser.add_argument('--mode', choices=['readonly', 'warn', 'block'],
                       default='warn', help='Modalità operativa (default: warn)')
    parser.add_argument('--target', help='Istanza Claude Code target da monitorare')
    parser.add_argument('--dashboard', action='store_true',
                       help='Abilita dashboard di monitoraggio')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Output verboso')

    args = parser.parse_args()

    # Crea e configura agente
    config_path = args.config or 'config/agent_config.yaml'
    agent = AuditorAgent(config_path)

    # Override config da CLI
    if args.mode:
        agent.config.mode = args.mode
    if args.target:
        agent.config.target_instance = args.target
    if args.dashboard:
        agent.config.enable_dashboard = True
    if args.verbose:
        agent.config.verbose = True

    # Setup signal handler per graceful shutdown
    def signal_handler(signum, frame):
        agent.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Avvia agente
    agent.start()


if __name__ == '__main__':
    main()
