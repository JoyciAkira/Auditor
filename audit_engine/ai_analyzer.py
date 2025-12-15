"""
AI Analyzer - Usa LLM reale per analisi intelligente.
Integra Ollama/CodeGeeX per andare oltre il pattern matching.
"""

import json
from typing import Dict, Optional, Any
from .ollama_client import OllamaClient
from .auditor import AuditResult


class AIAnalyzer:
    """Analyzer che usa LLM per analisi intelligente del codice."""

    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "codegeex"):
        """Inizializza analyzer con Ollama client."""
        self.client = OllamaClient(ollama_url, model)

    def test_connection(self) -> bool:
        """Test connessione al LLM."""
        return self.client.test_connection()

    def analyze_event(self, event: Dict[str, Any]) -> Optional[AuditResult]:
        """Analizza un evento usando LLM per ragionamento intelligente."""

        event_type = event.get('type', '')

        if event_type == 'tool':
            return self._analyze_tool_event(event)
        elif event_type == 'status':
            return self._analyze_status_event(event)
        elif event_type == 'lifecycle':
            return self._analyze_lifecycle_event(event)

        return None

    def _analyze_tool_event(self, event: Dict[str, Any]) -> Optional[AuditResult]:
        """Analizza evento tool con LLM."""

        tool_name = event.get('tool_name', '')
        tool_input = event.get('tool_input', {})

        if tool_name == 'Bash':
            return self._analyze_bash_command_ai(tool_input)
        elif tool_name == 'FileEdit':
            return self._analyze_file_edit_ai(tool_input)

        return None

    def _analyze_bash_command_ai(self, tool_input: Dict) -> Optional[AuditResult]:
        """Analizza comando bash con LLM."""

        command = tool_input.get('command', '')

        analysis = self.client.analyze_code(
            f"Comando shell: {command}",
            context={"type": "bash_command", "command": command}
        )

        if analysis:
            # Estrai livello rischio dall'analisi AI
            risk_level = self._extract_risk_level(analysis)

            return AuditResult(
                rule_name="ai_bash_analysis",
                severity=risk_level,
                action=self._risk_to_action(risk_level),
                description="Analisi AI comando bash",
                evidence=command,
                suggestion=analysis[:500] + "..." if len(analysis) > 500 else analysis
            )

        return None

    def _analyze_file_edit_ai(self, tool_input: Dict) -> Optional[AuditResult]:
        """Analizza modifica file con LLM."""

        file_path = tool_input.get('file_path', '')
        new_string = tool_input.get('new_string', '')

        # Pre-filtra con pattern matching veloce
        if self._quick_pattern_check(new_string):
            # Usa LLM per analisi profonda
            analysis = self.client.analyze_code(
                new_string,
                context={
                    "file_path": file_path,
                    "operation": "file_edit"
                }
            )

            if analysis:
                risk_level = self._extract_risk_level(analysis)

                return AuditResult(
                    rule_name="ai_code_analysis",
                    severity=risk_level,
                    action=self._risk_to_action(risk_level),
                    description=f"Analisi AI modifica file: {file_path}",
                    location=file_path,
                    evidence=new_string[:300] + "..." if len(new_string) > 300 else new_string,
                    suggestion=analysis[:800] + "..." if len(analysis) > 800 else analysis
                )

        return None

    def _analyze_status_event(self, event: Dict[str, Any]) -> Optional[AuditResult]:
        """Analizza evento status con LLM."""

        status_detail = event.get('status_detail', '')

        if 'commit' in status_detail.lower():
            # Analizza qualità commit con LLM
            analysis = self.client.analyze_commit(status_detail, "changes summary")

            if analysis:
                return AuditResult(
                    rule_name="ai_commit_analysis",
                    severity="low",  # I commit sono generalmente low risk
                    action="suggest",
                    description="Analisi AI qualità commit",
                    evidence=status_detail,
                    suggestion=analysis[:500] + "..." if len(analysis) > 500 else analysis
                )

        return None

    def _analyze_lifecycle_event(self, event: Dict[str, Any]) -> Optional[AuditResult]:
        """Analizza eventi lifecycle."""
        # Per ora, lifecycle events non richiedono AI analysis
        return None

    def _quick_pattern_check(self, code: str) -> bool:
        """Controllo veloce per decidere se usare LLM."""
        # Pattern che giustificano analisi AI
        ai_patterns = [
            'import os', 'import subprocess', 'exec(', 'eval(',
            'password', 'secret', 'key', 'token',
            'sql', 'query', 'execute',
            'def ', 'class ',  # Funzioni/classe complesse
        ]

        return any(pattern in code.lower() for pattern in ai_patterns)

    def _extract_risk_level(self, analysis: str) -> str:
        """Estrae livello rischio dal testo dell'analisi AI."""

        analysis_lower = analysis.lower()

        if 'critical' in analysis_lower:
            return 'critical'
        elif 'high' in analysis_lower:
            return 'high'
        elif 'medium' in analysis_lower:
            return 'medium'
        elif 'low' in analysis_lower:
            return 'low'
        else:
            # Default basato su presenza di parole chiave negative
            negative_words = ['vulnerability', 'security', 'risk', 'dangerous', 'unsafe']
            if any(word in analysis_lower for word in negative_words):
                return 'medium'
            return 'low'

    def _risk_to_action(self, risk_level: str) -> str:
        """Converte livello rischio in azione appropriata."""

        actions = {
            'critical': 'block',
            'high': 'block',
            'medium': 'warn',
            'low': 'suggest'
        }

        return actions.get(risk_level, 'suggest')

    def get_stats(self) -> Dict[str, Any]:
        """Statistiche di utilizzo LLM."""
        # Qui potremmo trackare token usati, tempi di risposta, etc.
        return {
            "llm_enabled": True,
            "model": self.client.model,
            "connection_status": "connected" if self.test_connection() else "disconnected"
        }
