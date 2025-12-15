"""
Client per integrazione con Ollama LLM (CodeGeeX).
Permette analisi AI reale invece di mock responses.
"""

import requests
import json
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass


@dataclass
class OllamaResponse:
    """Risposta da Ollama API."""
    content: str
    tokens_used: int = 0
    model: str = ""
    total_duration: float = 0.0
    eval_duration: float = 0.0


class OllamaClient:
    """Client per comunicare con Ollama API."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "codegeex"):
        """Inizializza client Ollama.

        Args:
            base_url: URL base dell'API Ollama (default: localhost:11434)
            model: Nome del modello da usare (default: codegeex)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = 30  # secondi

    def test_connection(self) -> bool:
        """Test connessione a Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                print(f"✅ Connesso a Ollama. Modelli disponibili: {model_names}")

                if self.model not in model_names:
                    print(f"⚠️  Modello '{self.model}' non trovato. Disponibili: {model_names}")
                    return False

                return True
            else:
                print(f"❌ Errore connessione Ollama: HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Errore connessione Ollama: {e}")
            return False

    def chat_completion(self, messages: List[Dict[str, str]],
                       temperature: float = 0.1,
                       max_tokens: int = 1000) -> Optional[OllamaResponse]:
        """Invia richiesta chat completion a Ollama."""

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                end_time = time.time()

                return OllamaResponse(
                    content=data.get('message', {}).get('content', ''),
                    tokens_used=data.get('eval_count', 0),
                    model=data.get('model', self.model),
                    total_duration=end_time - start_time,
                    eval_duration=data.get('eval_duration', 0) / 1e9  # Converti nanosecondi a secondi
                )
            else:
                print(f"❌ Errore Ollama API: HTTP {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            print(f"❌ Timeout Ollama ({self.timeout}s)")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Errore richiesta Ollama: {e}")
            return None
        except json.JSONDecodeError:
            print("❌ Errore parsing risposta JSON da Ollama")
            return None

    def analyze_code(self, code: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Analizza codice con LLM per problemi di sicurezza/qualità."""

        context_str = ""
        if context:
            context_str = f"\nContesto: {json.dumps(context, indent=2)}"

        prompt = f"""Analizza questo frammento di codice per problemi di sicurezza, qualità e best practices:

{code}{context_str}

Fornisci un'analisi dettagliata che includa:
1. Livello di rischio (LOW/MEDIUM/HIGH/CRITICAL)
2. Problemi specifici identificati
3. Suggerimenti per miglioramento
4. Eventuali vulnerabilità di sicurezza

Rispondi in italiano se possibile, ma mantieni termini tecnici in inglese quando appropriato."""

        messages = [{"role": "user", "content": prompt}]

        response = self.chat_completion(messages, temperature=0.1, max_tokens=800)

        if response:
            return response.content
        return None

    def analyze_commit(self, commit_message: str, changes: str) -> Optional[str]:
        """Analizza un commit per qualità e completezza."""

        prompt = f"""Analizza questo commit per qualità, completezza e aderenza alle best practices:

Messaggio commit: {commit_message}

Cambimenti:
{changes}

Valuta:
1. Chiarezza e completezza del messaggio
2. Atomicità dei cambiamenti
3. Presenza di test se applicabile
4. Qualità del codice modificato

Fornisci un feedback costruttivo."""

        messages = [{"role": "user", "content": prompt}]

        response = self.chat_completion(messages, temperature=0.2, max_tokens=600)

        if response:
            return response.content
        return None

    def get_available_models(self) -> List[str]:
        """Restituisce lista modelli disponibili."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m['name'] for m in models]
            return []
        except Exception:
            return []

    def get_model_info(self, model_name: str = None) -> Optional[Dict]:
        """Restituisce informazioni su un modello."""
        model = model_name or self.model

        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model},
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception:
            return None
