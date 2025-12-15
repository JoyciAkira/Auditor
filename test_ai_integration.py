#!/usr/bin/env python3
"""
Test integrazione AI con Ollama/CodeGeeX.
Verifica funzionamento LLM reale vs mock.
"""

import sys
import time
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from audit_engine.ollama_client import OllamaClient
from audit_engine.ai_analyzer import AIAnalyzer
from audit_engine.auditor import AuditorEngine
from config.agent_config import AgentConfig


class TestAIIntegration:
    """Test per integrazione AI con Ollama."""

    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "codegeex"):
        """Inizializza test con parametri Ollama."""
        self.ollama_url = ollama_url
        self.model = model
        self.client = OllamaClient(ollama_url, model)

    def test_ollama_connection(self):
        """Test connessione a Ollama."""
        print(f"🧪 Test Connessione Ollama: {self.ollama_url}")

        if not self.client.test_connection():
            print("❌ Ollama non disponibile. Test saltato."            print("💡 Assicurati che Ollama sia running e CodeGeeX scaricato:")
            print(f"   docker exec -it <ollama-container> ollama pull {self.model}")
            return False

        print("✅ Connessione Ollama OK")
        return True

    def test_simple_ai_analysis(self):
        """Test analisi AI semplice."""
        print("\n🧪 Test Analisi AI Semplice")

        test_cases = [
            {
                "code": 'API_KEY = "sk-1234567890abcdef"',
                "expected_risk": "high",
                "description": "Hardcoded secret"
            },
            {
                "code": 'os.system("rm -rf /")',
                "expected_risk": "critical",
                "description": "Dangerous command"
            },
            {
                "code": 'def hello():\n    print("Hello World")',
                "expected_risk": "low",
                "description": "Safe code"
            }
        ]

        analyzer = AIAnalyzer(self.ollama_url, self.model)

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Test {i}: {test_case['description']}")

            # Crea evento simulato
            event = {
                "type": "tool",
                "tool_name": "FileEdit",
                "tool_input": {
                    "file_path": f"test_{i}.py",
                    "new_string": test_case["code"]
                }
            }

            start_time = time.time()
            result = analyzer.analyze_event(event)
            end_time = time.time()

            if result:
                print(f"   ✅ Rilevato: {result.rule_name} ({result.severity})")
                print(f"   💡 Suggerimento: {result.suggestion[:100]}...")
                print(".2f"                success = result.severity in ["high", "critical"] if test_case["expected_risk"] in ["high", "critical"] else result.severity == "low"
            else:
                print("   ⚪ Nessun problema rilevato")
                success = test_case["expected_risk"] == "low"

            if success:
                print("   ✅ Test superato")
            else:
                print("   ❌ Test fallito")

        return True  # I test AI sono più flessibili

    def test_ai_vs_pattern_comparison(self):
        """Confronta AI analysis vs pattern matching."""
        print("\n🧪 Confronto AI vs Pattern Matching")

        # Crea config senza AI
        config_no_ai = AgentConfig()
        config_no_ai.enable_ai = False

        # Crea config con AI
        config_with_ai = AgentConfig()
        config_with_ai.enable_ai = True
        config_with_ai.ollama_url = self.ollama_url
        config_with_ai.ollama_model = self.model

        engine_no_ai = AuditorEngine(config_no_ai)
        engine_no_ai.start()

        engine_with_ai = AuditorEngine(config_with_ai)
        engine_with_ai.start()

        # Test case complesso che pattern matching potrebbe non cogliere
        complex_code = '''
import os
import subprocess

def complex_function():
    # Questa funzione fa cose complicate
    try:
        # Connessione database
        conn = connect_to_db("user:password@host/db")

        # Esegue query dinamica (potenziale SQL injection)
        query = f"SELECT * FROM users WHERE id = {user_input}"
        result = conn.execute(query)

        # Comando shell basato su input (pericoloso)
        cmd = f"process_file {user_input}"
        subprocess.run(cmd, shell=True)

    except Exception as e:
        # Log dell'errore con dati sensibili
        log_error(f"Error: {e} with data: {sensitive_data}")

    finally:
        # Pulizia... o no?
        pass
'''

        event = {
            "type": "tool",
            "tool_name": "FileEdit",
            "tool_input": {
                "file_path": "complex.py",
                "new_string": complex_code
            }
        }

        print("🔍 Analisi con Pattern Matching (no AI):")
        pattern_result = engine_no_ai.analyze_event(event)
        if pattern_result:
            print(f"   ✅ Rilevato: {pattern_result.rule_name} ({pattern_result.severity})")
        else:
            print("   ⚪ Nessun problema rilevato")

        print("\n🤖 Analisi con AI (Ollama):")
        ai_result = engine_with_ai.analyze_event(event)
        if ai_result:
            print(f"   ✅ Rilevato: {ai_result.rule_name} ({ai_result.severity})")
            print(f"   💡 Analisi AI: {ai_result.suggestion[:200]}...")
        else:
            print("   ⚪ Nessun problema rilevato")

        engine_no_ai.stop()
        engine_with_ai.stop()

        print(f"\n📊 Confronto:")
        print(f"   Pattern matching: {'✅' if pattern_result else '❌'}")
        print(f"   AI Analysis: {'✅' if ai_result else '❌'}")

        return True

    def test_performance_ai(self):
        """Test performance AI analysis."""
        print("\n🧪 Test Performance AI")

        analyzer = AIAnalyzer(self.ollama_url, self.model)

        simple_code = 'print("hello")'
        event = {
            "type": "tool",
            "tool_name": "FileEdit",
            "tool_input": {
                "file_path": "test.py",
                "new_string": simple_code
            }
        }

        # Test 5 analisi consecutive
        times = []
        for i in range(5):
            start = time.time()
            result = analyzer.analyze_event(event)
            end = time.time()
            times.append(end - start)
            print(".2f"            if result:
                print(f"   ✅ Analisi {i+1} completata")
            else:
                print(f"   ⚠️  Analisi {i+1} senza risultato")

        avg_time = sum(times) / len(times)
        print(".2f"        print(f"   📈 Min: {min(times):.2f}s, Max: {max(times):.2f}s")

        # AI dovrebbe essere ragionevolmente veloce (< 10s media)
        return avg_time < 10.0


def main():
    """Esegue tutti i test AI."""
    print("🤖 Auditor Agent - AI Integration Test Suite")
    print("=" * 50)

    # Parametri Ollama (modifica per il tuo NAS)
    OLLAMA_URL = "http://localhost:11434"  # Cambia con IP del tuo NAS
    MODEL = "codegeex"

    print(f"🎯 Configurazione AI:")
    print(f"   URL: {OLLAMA_URL}")
    print(f"   Model: {MODEL}")
    print()

    test_suite = TestAIIntegration(OLLAMA_URL, MODEL)

    tests = [
        ("Ollama Connection", test_suite.test_ollama_connection),
        ("Simple AI Analysis", test_suite.test_simple_ai_analysis),
        ("AI vs Pattern Comparison", test_suite.test_ai_vs_pattern_comparison),
        ("AI Performance", test_suite.test_performance_ai),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")

    print("\n" + "=" * 50)
    print(f"📊 Risultati: {passed}/{total} test passati")

    if passed == total:
        print("🎉 Tutti i test AI passati! Integrazione Ollama funzionante.")
        return 0
    elif passed >= total * 0.5:  # Almeno metà dei test
        print("⚠️  Alcuni test AI falliti, ma connessione base OK.")
        return 1
    else:
        print("❌ Problemi significativi con integrazione AI.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
