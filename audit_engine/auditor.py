"""
Motore di auditing principale.
Sistema ibrido: pattern matching veloce + AI analysis profonda.
"""

import re
import json
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from .ai_analyzer import AIAnalyzer
from .models.audit_result import AuditResult


@dataclass
class AuditRule:
    """Rappresenta una regola di auditing."""
    name: str
    pattern: Optional[str] = None
    severity: str = "medium"
    action: str = "warn"
    description: str = ""
    max_lines: Optional[int] = None
    require_tests: bool = False


class AuditorEngine:
    """Motore principale per l'auditing del codice e delle azioni."""

    def __init__(self, config):
        """Inizializza il motore di auditing."""
        self.config = config
        self.rules = self._load_rules()
        self.active = False

        # AI Analyzer (opzionale)
        self.ai_analyzer = None
        if hasattr(config, 'enable_ai') and config.enable_ai:
            try:
                ollama_url = getattr(config, 'ollama_url', 'http://localhost:11434')
                ollama_model = getattr(config, 'ollama_model', 'codegeex')
                ai_timeout = int(getattr(config, 'ai_timeout', 30))
                ai_temperature = float(getattr(config, 'ai_temperature', 0.1))
                self.ai_analyzer = AIAnalyzer(ollama_url, ollama_model, timeout_seconds=ai_timeout, temperature=ai_temperature)
                print(f"🤖 AI Analyzer inizializzato: {ollama_model} @ {ollama_url}")
            except Exception as e:
                print(f"⚠️  AI Analyzer non disponibile: {e}")
                self.ai_analyzer = None

        # Statistiche
        self.stats = {
            'events_processed': 0,
            'issues_found': 0,
            'warnings_sent': 0,
            'blocks_applied': 0,
            'ai_analyses': 0,
            'pattern_matches': 0
        }

    def start(self):
        """Avvia il motore di auditing."""
        self.active = True
        print(f"🔍 Motore di auditing avviato con {len(self.rules)} regole")

    def stop(self):
        """Ferma il motore di auditing."""
        self.active = False
        print("🛑 Motore di auditing fermato")
        self._print_stats()

    def analyze_event(self, event: Dict) -> Optional[AuditResult]:
        """Analizza un evento e restituisce il risultato dell'audit."""
        if not self.active:
            return None

        self.stats['events_processed'] += 1

        # Prima: Pattern matching veloce
        pattern_result = self._analyze_with_patterns(event)
        if pattern_result:
            self.stats['pattern_matches'] += 1
            self.update_stats(pattern_result)
            return pattern_result

        # Secondo: AI analysis se disponibile e evento merita attenzione
        if self.ai_analyzer and self._should_use_ai(event):
            ai_result = self.ai_analyzer.analyze_event(event)
            if ai_result:
                self.stats['ai_analyses'] += 1
                self.update_stats(ai_result)
                return ai_result

        return None

    def _analyze_with_patterns(self, event: Dict) -> Optional[AuditResult]:
        """Analisi veloce con pattern matching."""
        event_type = event.get('type', '')

        # Routing basato sul tipo di evento
        if event_type == 'tool':
            result = self._analyze_tool_event(event)
        elif event_type == 'status':
            result = self._analyze_status_event(event)
        elif event_type == 'message':
            result = self._analyze_message_event(event)
        elif event_type == 'lifecycle':
            result = self._analyze_lifecycle_event(event)
        else:
            # Analisi generica
            result = self._analyze_generic_event(event)

        return result

    def _should_use_ai(self, event: Dict) -> bool:
        """Determina se un evento merita analisi AI."""
        event_type = event.get('type', '')

        if event_type == 'tool':
            tool_name = event.get('tool_name', '')
            if tool_name in ['Bash', 'FileEdit', 'RunTerminalCmd']:
                # Controlla contenuto per complessità
                tool_input = event.get('tool_input', {})
                if tool_name == 'FileEdit':
                    code = tool_input.get('new_string', '')
                    # Usa AI per codice complesso
                    return len(code) > 100 or self._contains_complex_patterns(code)
                elif tool_name == 'Bash':
                    command = tool_input.get('command', '')
                    # Usa AI per comandi complessi
                    return len(command) > 50 or '|' in command or '&&' in command
                elif tool_name == 'RunTerminalCmd':
                    return True  # Sempre usa AI per comandi terminal

        elif event_type == 'status':
            status_detail = event.get('status_detail', '')
            return 'commit' in status_detail.lower()  # Analizza commit con AI

        return False

    def _contains_complex_patterns(self, code: str) -> bool:
        """Controlla se codice contiene pattern complessi che meritano AI analysis."""
        complex_patterns = [
            'import ', 'def ', 'class ', 'try:', 'except:',
            'sql', 'query', 'execute', 'connect',
            'password', 'secret', 'key', 'token',
            'eval(', 'exec(', 'subprocess', 'os.system'
        ]
        return any(pattern in code.lower() for pattern in complex_patterns)

    def _analyze_tool_event(self, event: Dict) -> Optional[AuditResult]:
        """Analizza un evento tool (es. Bash, FileEdit)."""
        tool_name = event.get('tool_name', '')
        tool_input = event.get('tool_input', {})

        # Analisi specifica per tool
        if tool_name == 'Bash':
            return self._analyze_bash_command(tool_input)
        elif tool_name == 'FileEdit':
            return self._analyze_file_edit(tool_input)
        elif tool_name == 'RunTerminalCmd':
            return self._analyze_terminal_command(tool_input)

        return None

    def _analyze_bash_command(self, tool_input: Dict) -> Optional[AuditResult]:
        """Analizza un comando bash."""
        command = tool_input.get('command', '')

        # Controlli di sicurezza per comandi bash
        dangerous_patterns = [
            (r'rm\s+-rf\s+/', 'dangerous_rm', 'high', 'block'),
            (r'>/dev/null', 'redirect_dev_null', 'medium', 'warn'),
            (r'chmod\s+777', 'excessive_permissions', 'medium', 'warn'),
            (r'curl.*\|.*bash', 'pipe_to_bash', 'high', 'block'),
            (r'wget.*\|.*sh', 'pipe_to_sh', 'high', 'block'),
        ]

        for pattern, rule_name, severity, action in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return AuditResult(
                    rule_name=rule_name,
                    severity=severity,
                    action=action,
                    description=f"Comando potenzialmente pericoloso rilevato: {pattern}",
                    evidence=command[:100] + "..." if len(command) > 100 else command,
                    suggestion=self._get_command_suggestion(rule_name)
                )

        return None

    def _analyze_file_edit(self, tool_input: Dict) -> Optional[AuditResult]:
        """Analizza una modifica file."""
        file_path = tool_input.get('file_path', '')
        old_string = tool_input.get('old_string', '')
        new_string = tool_input.get('new_string', '')

        # Controlli di sicurezza sul contenuto
        issues = []

        # Controllo hardcoded secrets
        secrets_pattern = r'(?i)(password|secret|key|token|api_key).*?[\'"]([^\'"]{10,})[\'"]'
        if re.search(secrets_pattern, new_string):
            issues.append(('hardcoded_secrets', 'high', 'block'))

        # Controllo funzioni troppo lunghe
        if self._is_long_function(new_string):
            issues.append(('large_function', 'medium', 'warn'))

        # Controllo SQL injection patterns
        sql_patterns = [r'execute\(.*\+.*\)', r'cursor\.execute\(.*%.*\)']
        for pattern in sql_patterns:
            if re.search(pattern, new_string):
                issues.append(('sql_injection_risk', 'high', 'block'))

        if issues:
            rule_name, severity, action = issues[0]  # Prendi il primo issue
            return AuditResult(
                rule_name=rule_name,
                severity=severity,
                action=action,
                description=f"Problema rilevato nella modifica del file {file_path}",
                location=file_path,
                evidence=new_string[:200] + "..." if len(new_string) > 200 else new_string,
                suggestion=self._get_file_edit_suggestion(rule_name)
            )

        return None

    def _analyze_terminal_command(self, tool_input: Dict) -> Optional[AuditResult]:
        """Analizza un comando terminale."""
        command = tool_input.get('command', '')
        is_background = tool_input.get('is_background', False)

        # Comandi che dovrebbero essere confermati
        confirm_commands = [
            'git push',
            'docker push',
            'npm publish',
            'pip upload',
        ]

        for cmd in confirm_commands:
            if cmd in command:
                return AuditResult(
                    rule_name='critical_command',
                    severity='high',
                    action='warn',
                    description=f"Comando critico rilevato che richiede conferma: {cmd}",
                    evidence=command,
                    suggestion="Conferma manuale richiesta per comando critico"
                )

        return None

    def _analyze_status_event(self, event: Dict) -> Optional[AuditResult]:
        """Analizza un evento di status."""
        status_detail = event.get('status_detail', '')

        # Controllo commit senza test
        if 'commit' in status_detail.lower():
            # Qui potremmo controllare se ci sono test modificati
            # Per ora, semplice controllo presenza "test" nel messaggio
            if 'test' not in status_detail.lower():
                return AuditResult(
                    rule_name='commit_without_tests',
                    severity='low',
                    action='suggest',
                    description="Commit rilevato senza riferimento a test",
                    suggestion="Considera di aggiungere test per questa modifica"
                )

        return None

    def _analyze_message_event(self, event: Dict) -> Optional[AuditResult]:
        """Analizza un evento messaggio."""
        # Per ora, analisi minima sui messaggi
        return None

    def _analyze_lifecycle_event(self, event: Dict) -> Optional[AuditResult]:
        """Analizza un evento lifecycle."""
        # Controllo sessioni troppo lunghe o comportamenti anomali
        return None

    def _analyze_generic_event(self, event: Dict) -> Optional[AuditResult]:
        """Analisi generica per eventi non specifici."""
        # Controllo pattern generici di sicurezza
        event_json = json.dumps(event)

        for rule in self.rules:
            if rule.pattern and re.search(rule.pattern, event_json, re.IGNORECASE):
                return AuditResult(
                    rule_name=rule.name,
                    severity=rule.severity,
                    action=rule.action,
                    description=rule.description,
                    evidence=event_json[:200] + "..." if len(event_json) > 200 else event_json
                )

        return None

    def _is_long_function(self, code: str) -> bool:
        """Controlla se il codice contiene funzioni troppo lunghe."""
        # Semplice euristica: conta le linee
        lines = len(code.split('\n'))
        return lines > 50  # Configurabile

    def _get_command_suggestion(self, rule_name: str) -> str:
        """Restituisce un suggerimento per un problema di comando."""
        suggestions = {
            'dangerous_rm': "Usa 'rm -rf' con cautela. Considera backup o controllo manuale.",
            'redirect_dev_null': "Il redirect a /dev/null nasconde output. Usa con attenzione.",
            'excessive_permissions': "chmod 777 concede troppi permessi. Usa permessi specifici.",
            'pipe_to_bash': "Eseguire script remoti via pipe è rischioso. Scarica e verifica prima.",
            'pipe_to_sh': "Eseguire script remoti via pipe è rischioso. Scarica e verifica prima."
        }
        return suggestions.get(rule_name, "Rivedi il comando per sicurezza")

    def _get_file_edit_suggestion(self, rule_name: str) -> str:
        """Restituisce un suggerimento per un problema di modifica file."""
        suggestions = {
            'hardcoded_secrets': "Non hardcodare segreti. Usa variabili d'ambiente o vault.",
            'large_function': "Funzione troppo lunga. Considera di suddividerla in funzioni più piccole.",
            'sql_injection_risk': "Possibile SQL injection. Usa prepared statements o ORM."
        }
        return suggestions.get(rule_name, "Rivedi il codice per best practices")

    def _load_rules(self) -> List[AuditRule]:
        """Carica le regole di auditing dalla configurazione."""
        rules_file = Path(self.config.rules_path)
        if not rules_file.exists():
            print(f"⚠️  File regole non trovato: {rules_file}")
            return self._get_default_rules()

        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                rules_data = yaml.safe_load(f)

            rules = []
            for category, category_rules in rules_data.items():
                for rule_data in category_rules:
                    rules.append(AuditRule(**rule_data))

            return rules

        except Exception as e:
            print(f"⚠️  Errore caricamento regole: {e}")
            return self._get_default_rules()

    def _get_default_rules(self) -> List[AuditRule]:
        """Restituisce regole di default."""
        return [
            AuditRule(
                name="hardcoded_secrets",
                pattern=r'(?i)(password|secret|key|token).*?[\'"]([^\'"]{10,})[\'"]',
                severity="high",
                action="block",
                description="Possibili segreti hardcodati rilevati"
            ),
            AuditRule(
                name="dangerous_commands",
                pattern=r'(rm\s+-rf\s+/|curl.*\|\s*bash|wget.*\|\s*sh)',
                severity="high",
                action="block",
                description="Comandi potenzialmente distruttivi rilevati"
            )
        ]

    def _print_stats(self):
        """Stampa le statistiche finali."""
        print("\n📊 Statistiche Auditor Engine:")
        print(f"   Eventi processati: {self.stats['events_processed']}")
        print(f"   Problemi rilevati: {self.stats['issues_found']}")
        print(f"   Avvisi inviati: {self.stats['warnings_sent']}")
        print(f"   Blocchi applicati: {self.stats['blocks_applied']}")

    def update_stats(self, result: AuditResult):
        """Aggiorna le statistiche dopo un risultato."""
        self.stats['issues_found'] += 1

        if result.action == 'warn':
            self.stats['warnings_sent'] += 1
        elif result.action == 'block':
            self.stats['blocks_applied'] += 1
