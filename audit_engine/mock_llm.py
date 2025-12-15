"""
Mock LLM per testing senza API reali.
Simula risposte AI basate su pattern predefiniti.
"""

import re
import json
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class MockLLMResponse:
    """Risposta simulata da LLM."""
    content: str
    tokens_used: int = 100
    finish_reason: str = "stop"


class MockLLM:
    """Mock LLM che simula risposte AI basate su pattern."""

    def __init__(self, responses_file: Optional[str] = None):
        """Inizializza mock con risposte predefinite."""
        self.responses_file = responses_file or "audit_engine/mock_responses.json"
        self.responses = self._load_responses()

        # Statistiche per test
        self.call_count = 0
        self.last_prompt = ""
        self.last_response = ""

    def _load_responses(self) -> Dict[str, str]:
        """Carica risposte predefinite da file JSON."""
        try:
            with open(self.responses_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Risposte di default se file non esiste
            return self._get_default_responses()

    def _get_default_responses(self) -> Dict[str, str]:
        """Risposte predefinite per testing."""
        return {
            "security_analysis": """
            Analisi di sicurezza del codice:

            LIVELLO RISCHIO: HIGH

            Problemi identificati:
            1. Possibile SQL injection nella query dinamica
            2. Mancanza di sanitizzazione input utente
            3. Esposizione di informazioni sensibili nei log

            Suggerimenti:
            - Usa prepared statements per query SQL
            - Implementa input validation lato server
            - Rimuovi dati sensibili dai log di errore
            """,

            "code_quality": """
            Analisi qualità codice:

            LIVELLO QUALITÀ: MEDIUM

            Aspetti positivi:
            - Buona struttura generale
            - Commenti adeguati

            Miglioramenti suggeriti:
            - Ridurre complessità funzioni (max 20 righe)
            - Aggiungere test unitari per funzioni critiche
            - Migliorare gestione errori con eccezioni specifiche
            """,

            "hardcoded_secret": """
            Rilevato hardcoded secret:

            LIVELLO RISCHIO: CRITICAL

            Il codice contiene credenziali hardcodate che rappresentano
            un rischio di sicurezza grave. Le chiavi API e password
            dovrebbero essere gestite tramite variabili d'ambiente
            o sistemi di secret management.
            """,

            "dangerous_command": """
            Comando shell potenzialmente pericoloso rilevato:

            LIVELLO RISCHIO: HIGH

            Il comando 'rm -rf /' può causare perdita irreversibile di dati.
            Suggerisco di:
            - Aggiungere controlli di sicurezza
            - Richiedere conferma esplicita
            - Usare percorsi relativi invece di assoluti
            """
        }

    def chat_completion(self, messages: list, **kwargs) -> MockLLMResponse:
        """Simula chiamata ChatCompletion."""
        self.call_count += 1

        # Estrai il prompt dall'ultimo messaggio
        prompt = ""
        if messages and len(messages) > 0:
            prompt = messages[-1].get('content', '')
            self.last_prompt = prompt

        # Determina tipo di analisi basato sul prompt
        response_key = self._classify_prompt(prompt)

        # Ottieni risposta corrispondente
        response_content = self.responses.get(response_key, self._get_fallback_response())
        self.last_response = response_content

        return MockLLMResponse(
            content=response_content,
            tokens_used=len(response_content.split())
        )

    def _classify_prompt(self, prompt: str) -> str:
        """Classifica il prompt per determinare il tipo di risposta."""
        prompt_lower = prompt.lower()

        if 'secret' in prompt_lower or 'password' in prompt_lower or 'api_key' in prompt_lower:
            return 'hardcoded_secret'

        if 'rm -rf' in prompt_lower or 'dangerous' in prompt_lower or 'command' in prompt_lower:
            return 'dangerous_command'

        if 'security' in prompt_lower or 'vulnerability' in prompt_lower or 'risk' in prompt_lower:
            return 'security_analysis'

        if 'quality' in prompt_lower or 'maintainability' in prompt_lower or 'complexity' in prompt_lower:
            return 'code_quality'

        return 'security_analysis'  # Default

    def _get_fallback_response(self) -> str:
        """Risposta di fallback generica."""
        return """
        Analisi completata:

        LIVELLO RISCHIO: LOW

        Il codice analizzato non presenta problemi evidenti di sicurezza
        o qualità. Continua a monitorare le best practices di sviluppo.
        """

    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche delle chiamate mock."""
        return {
            'call_count': self.call_count,
            'last_prompt': self.last_prompt[:200] + "..." if len(self.last_prompt) > 200 else self.last_prompt,
            'last_response': self.last_response[:200] + "..." if len(self.last_response) > 200 else self.last_response
        }

    def reset_stats(self):
        """Reset statistiche per nuovo test."""
        self.call_count = 0
        self.last_prompt = ""
        self.last_response = ""
