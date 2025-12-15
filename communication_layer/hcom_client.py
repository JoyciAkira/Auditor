"""
Client per l'integrazione con claude-hook-comms (hcom).
Gestisce la comunicazione con il sistema di hook di Claude Code.
"""

import json
import subprocess
from typing import List, Dict, Optional, Any
import hashlib


class HComClient:
    """Client per comunicare con claude-hook-comms."""

    def __init__(self, config):
        """Inizializza il client hcom."""
        self.config = config
        self.connected = False
        self.agent_name = config.agent_name or "auditor"
        self._seen_event_fingerprints: set[str] = set()
        self._seen_max = 2000

        # Preferisci API Python se disponibili (contratto verificato in claude-hook-comms/src/hcom/api.py)
        self._hcom_api = None

    def connect(self):
        """Connette al sistema hcom."""
        try:
            try:
                from hcom import api as hapi  # type: ignore
                self._hcom_api = hapi
                # Smoke test: deve poter query-are eventi/istanze (inizializza DB internamente)
                _ = self._hcom_api.events(last=1)
                print("✅ Connesso a hcom (API Python)")
                self.connected = True
                self._register_agent()
                return
            except Exception:
                # Fallback: CLI
                self._hcom_api = None
                result = subprocess.run(['hcom', 'list'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print("✅ Connesso a hcom (CLI)")
                    self.connected = True
                    self._register_agent()
                    return
                raise Exception(f"hcom non disponibile: {result.stderr}")

        except FileNotFoundError:
            raise Exception("hcom non installato. Installa con: pip install hcom")
        except Exception as e:
            raise Exception(f"Errore connessione hcom: {e}")

    def disconnect(self):
        """Disconnette dal sistema hcom."""
        if self.connected:
            try:
                # Potrebbe essere necessario cleanup specifico
                self._unregister_agent()
            except Exception as e:
                print(f"⚠️  Errore durante la disconnessione: {e}")

            self.connected = False
            print("👋 Disconnesso da claude-hook-comms")

    def _register_agent(self):
        """Registra questo agente nel sistema hcom."""
        try:
            self.send_message(f"Agente auditor {self.agent_name} connesso e operativo", intent="inform")
            # Subscriptions: opzionali. Se CLI, richiedono contesto/istanza; non garantito per sender esterni.
            # Per affidabilità, qui NON le imponiamo automaticamente.

        except Exception as e:
            print(f"⚠️  Errore registrazione agente: {e}")

    def _unregister_agent(self):
        """Rimuove la registrazione dell'agente."""
        try:
            self.send_message(f"Agente auditor {self.agent_name} disconnesso", intent="inform")
        except Exception:
            pass  # Ignora errori durante la disconnessione

    def get_new_events(self) -> List[Dict]:
        """Recupera nuovi eventi dal sistema hcom."""
        if not self.connected:
            return []

        try:
            # Via API Python: ritorna lista di dict {ts,type,instance,data}
            if self._hcom_api:
                raw_events = self._hcom_api.events(last=50)
                return self._dedupe_events(raw_events)

            # Fallback CLI: hcom events stampa 1 JSON per riga (contratto verificato in cmd_events)
            cmd = ['hcom', 'events', '--last', '50']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print(f"⚠️  Errore recupero eventi: {result.stderr}")
                return []

            events: list[dict] = []
            for line in (result.stdout or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return self._dedupe_events(events)

        except subprocess.TimeoutExpired:
            print("⚠️  Timeout recupero eventi")
            return []
        except Exception as e:
            print(f"⚠️  Errore recupero eventi: {e}")
            return []

    def send_message(self, message: str, to: Optional[str] = None,
                    intent: str = "inform") -> bool:
        """Invia un messaggio attraverso hcom."""
        if not self.connected:
            return False

        try:
            if self._hcom_api:
                self._hcom_api.send(message, to=to, sender=self.agent_name, intent=intent)
                return True

            # CLI: non esiste --to; per target si usa @mention nel testo (contratto verificato in cmd_send)
            if to and not message.lstrip().startswith(f"@{to}"):
                message = f"@{to} {message}"
            cmd = ['hcom', 'send', '--from', self.agent_name, '--intent', intent, message]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print(f"⚠️  Errore invio messaggio: {result.stderr}")
                return False
            return True

        except Exception as e:
            print(f"⚠️  Errore invio messaggio: {e}")
            return False

    def get_instance_transcript(self, instance_name: str,
                              last_n: int = 10) -> Optional[Dict]:
        """Recupera il transcript di un'istanza specifica."""
        if not self.connected:
            return None

        try:
            # Non implemento qui parsing transcript via API per evitare supposizioni sul formato.
            cmd = ['hcom', 'transcript', f'@{instance_name}', '--last', str(last_n), '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                print(f"⚠️  Errore recupero transcript: {result.stderr}")
                return None
            return json.loads(result.stdout)

        except Exception as e:
            print(f"⚠️  Errore recupero transcript: {e}")
            return None

    def get_active_instances(self) -> List[Dict]:
        """Recupera lista delle istanze attive."""
        if not self.connected:
            return []

        try:
            if self._hcom_api:
                return self._hcom_api.instances(all=False)  # enabled_only

            cmd = ['hcom', 'list', '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print(f"⚠️  Errore recupero istanze: {result.stderr}")
                return []
            # Nota: hcom list --json emette JSON per riga (payload _self + 1 riga per istanza)
            instances: list[dict] = []
            for line in (result.stdout or "").splitlines():
                try:
                    instances.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return instances

        except Exception as e:
            print(f"⚠️  Errore recupero istanze: {e}")
            return []

    def block_instance_action(self, instance_name: str, reason: str) -> bool:
        """Blocca un'azione di un'istanza (se supportato dal sistema)."""
        message = f"🚫 AUDIT BLOCK: {reason}"
        return self.send_message(message, to=instance_name, intent="error")

    def warn_instance(self, instance_name: str, warning: str) -> bool:
        """Invia un avviso a un'istanza."""
        message = f"⚠️  AUDIT WARNING: {warning}"
        return self.send_message(message, to=instance_name, intent="warn")

    def _dedupe_events(self, events: List[Dict]) -> List[Dict]:
        """Deduplica eventi perché API/CLI non espongono un id monotono nel payload."""
        out: list[dict] = []
        for ev in events:
            fp = hashlib.sha256(json.dumps(ev, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            if fp in self._seen_event_fingerprints:
                continue
            self._seen_event_fingerprints.add(fp)
            out.append(ev)
        # pruning
        if len(self._seen_event_fingerprints) > self._seen_max:
            # Strategia semplice: reset. Limite: possibile rielaborazione eventi vecchi.
            self._seen_event_fingerprints.clear()
        return out
