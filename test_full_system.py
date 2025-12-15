#!/usr/bin/env python3
"""
Test completi del sistema Auditor Agent senza LLM reali.
Usa mock LLM per simulare analisi AI.
"""

import sys
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from audit_engine.auditor import AuditorEngine
from audit_engine.mock_llm import MockLLM
from communication_layer.hcom_client import HComClient
from config.agent_config import AgentConfig


class TestFullSystem:
    """Test end-to-end del sistema completo con mock."""

    def __init__(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_llm = MockLLM()

    def setup_config(self) -> AgentConfig:
        """Crea configurazione di test."""
        config_path = self.temp_dir / "test_config.yaml"
        config_content = """
agent:
  name: "test-auditor"
  mode: "warn"
  target_instance: null
  enable_dashboard: false
  verbose: true

auditing:
  rules_path: "config/audit_rules.yaml"
  enable_security_checks: true
  enable_quality_checks: true
  enable_compliance_checks: true

communication:
  hcom_timeout: 5
  poll_interval: 0.1
"""
        config_path.write_text(config_content)

        # Mock per evitare lettura file
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = config_content
            config = AgentConfig(str(config_path))

        return config

    def test_pattern_based_auditing(self):
        """Test sistema di auditing basato su pattern (senza LLM)."""
        print("🧪 Test Pattern-Based Auditing...")

        config = self.setup_config()
        engine = AuditorEngine(config)
        engine.start()

        test_cases = [
            # (event, expected_problems)
            ({
                "type": "tool",
                "tool_name": "Bash",
                "tool_input": {"command": "rm -rf /tmp/test"}
            }, 1),  # dangerous_rm

            ({
                "type": "tool",
                "tool_name": "FileEdit",
                "tool_input": {
                    "file_path": "config.py",
                    "old_string": "",
                    "new_string": "API_KEY = 'sk-1234567890abcdef'"
                }
            }, 1),  # hardcoded_secrets

            ({
                "type": "status",
                "status_detail": "commit: Add new feature"
            }, 1),  # commit_without_tests

            ({
                "type": "tool",
                "tool_name": "FileEdit",
                "tool_input": {
                    "file_path": "utils.py",
                    "old_string": "",
                    "new_string": "def complex_function():\n" + "    pass\n" * 60
                }
            }, 1),  # large_function
        ]

        total_problems = 0
        for i, (event, expected) in enumerate(test_cases, 1):
            result = engine.analyze_event(event)
            if result:
                total_problems += 1
                print(f"   ✅ Test {i}: Rilevato {result.rule_name} ({result.severity})")
            else:
                print(f"   ❌ Test {i}: Nessun problema rilevato (atteso {expected})")

        engine.stop()

        success = total_problems == len(test_cases)
        print(f"   📊 Risultato: {total_problems}/{len(test_cases)} pattern corretti")
        return success

    def test_mock_llm_integration(self):
        """Test integrazione con mock LLM."""
        print("\n🧪 Test Mock LLM Integration...")

        # Test chiamate mock
        responses = []

        test_prompts = [
            "Analizza questo hardcoded secret: API_KEY = 'sk-123'",
            "Controlla questo comando pericoloso: rm -rf /",
            "Valuta qualità di questa funzione molto lunga",
            "Analizza rischio SQL injection"
        ]

        for prompt in test_prompts:
            response = self.mock_llm.chat_completion([
                {"role": "user", "content": prompt}
            ])
            responses.append(response)
            print(f"   📝 Prompt: {prompt[:50]}...")
            print(f"   🤖 Response: {response.content[:100]}...")

        # Verifica statistiche
        stats = self.mock_llm.get_stats()
        success = stats['call_count'] == len(test_prompts)

        print(f"   📊 Chiamate LLM: {stats['call_count']}")
        return success

    def test_config_loading(self):
        """Test caricamento configurazione."""
        print("\n🧪 Test Config Loading...")

        config = self.setup_config()

        # Verifica valori caricati
        checks = [
            config.agent_name == "test-auditor",
            config.mode == "warn",
            config.enable_dashboard == False,
            config.verbose == True
        ]

        success = all(checks)
        if success:
            print("   ✅ Configurazione caricata correttamente")
        else:
            print("   ❌ Errori nel caricamento configurazione")

        return success

    @patch('communication_layer.hcom_client.subprocess.run')
    def test_hcom_client_mock(self, mock_subprocess):
        """Test client hcom con mock subprocess."""
        print("\n🧪 Test HCom Client (Mock)...")

        # Mock risposte hcom
        mock_responses = {
            'hcom list': (0, '{"instances": [{"name": "alice"}, {"name": "bob"}]}'),
            'hcom send --from test-auditor --intent inform "test message"': (0, ''),
            'hcom events --sql "id > 0" --last 10 --json': (0, '{"events": []}'),
        }

        def mock_run(cmd_args, **kwargs):
            cmd_str = ' '.join(cmd_args)
            if cmd_str in mock_responses:
                exit_code, output = mock_responses[cmd_str]
                mock_result = MagicMock()
                mock_result.returncode = exit_code
                mock_result.stdout = output
                mock_result.stderr = ''
                return mock_result
            else:
                # Comando non previsto
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stdout = ''
                mock_result.stderr = f"Unknown command: {cmd_str}"
                return mock_result

        mock_subprocess.side_effect = mock_run

        config = self.setup_config()
        client = HComClient(config)

        # Test connessione
        try:
            client.connect()
            print("   ✅ Connessione hcom (mock) riuscita")
        except Exception as e:
            print(f"   ❌ Errore connessione: {e}")
            return False

        # Test invio messaggio
        success = client.send_message("Test message")
        if success:
            print("   ✅ Invio messaggio riuscito")
        else:
            print("   ❌ Invio messaggio fallito")

        # Test lettura eventi
        events = client.get_new_events()
        print(f"   📥 Eventi ricevuti: {len(events)}")

        client.disconnect()
        return True

    def test_end_to_end_pipeline(self):
        """Test pipeline completa end-to-end."""
        print("\n🧪 Test End-to-End Pipeline...")

        # Setup componenti
        config = self.setup_config()
        engine = AuditorEngine(config)
        engine.start()

        # Simula evento da hcom
        test_event = {
            "type": "tool",
            "tool_name": "FileEdit",
            "tool_input": {
                "file_path": "vulnerable.py",
                "old_string": "",
                "new_string": "API_KEY = 'sk-hardcoded-secret'\nimport os\nos.system('rm -rf /')"
            }
        }

        # Processa evento
        result = engine.analyze_event(test_event)

        if result:
            print(f"   🔍 Problema rilevato: {result.rule_name} ({result.severity})")
            print(f"   💡 Suggerimento: {result.suggestion}")

            # Simula gestione risultato
            if result.action == 'block':
                print("   🚫 Azione bloccata")
            elif result.action == 'warn':
                print("   ⚠️  Avviso inviato")
            elif result.action == 'suggest':
                print("   💡 Suggerimento fornito")

            success = True
        else:
            print("   ❌ Nessun problema rilevato (atteso almeno 1)")
            success = False

        engine.stop()

        # Verifica statistiche
        stats = engine.stats
        print(f"   📊 Eventi processati: {stats['events_processed']}")
        print(f"   🔍 Problemi trovati: {stats['issues_found']}")

        return success

    def test_performance(self):
        """Test performance del sistema."""
        print("\n🧪 Test Performance...")

        config = self.setup_config()
        engine = AuditorEngine(config)
        engine.start()

        # Genera eventi di test
        test_events = []
        for i in range(100):
            test_events.append({
                "type": "tool",
                "tool_name": "FileEdit",
                "tool_input": {
                    "file_path": f"file_{i}.py",
                    "old_string": "",
                    "new_string": f"def func_{i}():\n    api_key = 'sk-{i}'\n    return api_key"
                }
            })

        start_time = time.time()

        problems_found = 0
        for event in test_events:
            result = engine.analyze_event(event)
            if result:
                problems_found += 1

        end_time = time.time()
        duration = end_time - start_time

        engine.stop()

        throughput = len(test_events) / duration

        print(f"   ⏱️  Tempo totale: {duration:.2f}s")
        print(f"   📈 Throughput: {throughput:.1f} eventi/secondo")
        print(f"   🔍 Problemi trovati: {problems_found}/100")

        # Performance accettabile: > 50 eventi/secondo
        return throughput > 50

    def cleanup(self):
        """Pulizia ambiente test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    """Esegue tutti i test del sistema."""
    print("🚀 Auditor Agent - Full System Test Suite")
    print("=" * 50)

    test_suite = TestFullSystem()

    try:
        tests = [
            ("Pattern-Based Auditing", test_suite.test_pattern_based_auditing),
            ("Mock LLM Integration", test_suite.test_mock_llm_integration),
            ("Config Loading", test_suite.test_config_loading),
            ("HCom Client (Mock)", test_suite.test_hcom_client_mock),
            ("End-to-End Pipeline", test_suite.test_end_to_end_pipeline),
            ("Performance", test_suite.test_performance),
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
            print("🎉 Tutti i test passati! Sistema pronto per produzione (senza LLM).")
            return 0
        else:
            print("⚠️  Alcuni test falliti. Rivedi implementazione.")
            return 1

    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    sys.exit(main())
