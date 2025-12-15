#!/usr/bin/env python3
"""
Test scenari di failure per il sistema Auditor Agent.
Verifica comportamento in condizioni di errore.
"""

import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from audit_engine.auditor import AuditorEngine
from communication_layer.hcom_client import HComClient
from config.agent_config import AgentConfig


class TestFailureScenarios:
    """Test comportamento in scenari di failure."""

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_invalid_config_file(self):
        """Test caricamento config file invalido."""
        print("🧪 Test Invalid Config File...")

        invalid_config_path = self.temp_dir / "invalid.yaml"
        invalid_config_path.write_text("invalid: yaml: content: [")

        try:
            config = AgentConfig(str(invalid_config_path))
            print("   ❌ Config invalida caricata senza errori (atteso errore)")
            return False
        except Exception:
            print("   ✅ Config invalida correttamente rifiutata")
            return True

    def test_missing_rules_file(self):
        """Test comportamento con file regole mancante."""
        print("\n🧪 Test Missing Rules File...")

        config = MagicMock()
        config.rules_path = "nonexistent_rules.yaml"

        try:
            engine = AuditorEngine(config)
            engine.start()

            # Dovrebbe usare regole di default
            if len(engine.rules) > 0:
                print(f"   ✅ Regole di default caricate: {len(engine.rules)} regole")
                engine.stop()
                return True
            else:
                print("   ❌ Nessuna regola caricata")
                return False

        except Exception as e:
            print(f"   ❌ Errore caricamento regole: {e}")
            return False

    def test_hcom_connection_failure(self):
        """Test failure connessione hcom."""
        print("\n🧪 Test HCom Connection Failure...")

        config = MagicMock()
        config.agent_name = "test-auditor"

        client = HComClient(config)

        # Mock subprocess per simulare comando non trovato
        with patch('communication_layer.hcom_client.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("hcom command not found")

            try:
                client.connect()
                print("   ❌ Connessione riuscita quando doveva fallire")
                return False
            except Exception as e:
                if "hcom non installato" in str(e):
                    print("   ✅ Errore connessione gestito correttamente")
                    return True
                else:
                    print(f"   ❌ Errore inatteso: {e}")
                    return False

    def test_corrupt_event_data(self):
        """Test gestione eventi corrotti."""
        print("\n🧪 Test Corrupt Event Data...")

        config = MagicMock()
        config.rules_path = "config/audit_rules.yaml"

        engine = AuditorEngine(config)
        engine.start()

        corrupt_events = [
            None,  # Evento null
            {},    # Evento vuoto
            {"type": None},  # Type null
            {"type": "invalid_type"},  # Type sconosciuto
            {"type": "tool", "tool_name": None},  # Tool name null
        ]

        success_count = 0
        for i, event in enumerate(corrupt_events):
            try:
                result = engine.analyze_event(event)
                # Dovrebbe gestire graceful i dati corrotti
                success_count += 1
                print(f"   ✅ Evento corrotto {i+1} gestito senza crash")
            except Exception as e:
                print(f"   ❌ Evento corrotto {i+1} causò crash: {e}")

        engine.stop()

        success = success_count == len(corrupt_events)
        print(f"   📊 Eventi corrotti gestiti: {success_count}/{len(corrupt_events)}")
        return success

    def test_network_timeout_simulation(self):
        """Test simulazione timeout di rete."""
        print("\n🧪 Test Network Timeout Simulation...")

        config = MagicMock()
        config.agent_name = "test-auditor"

        client = HComClient(config)

        # Mock subprocess per simulare timeout
        with patch('communication_layer.hcom_client.subprocess.run') as mock_run:
            from subprocess import TimeoutExpired
            mock_run.side_effect = TimeoutExpired(cmd=["hcom", "list"], timeout=10)

            try:
                events = client.get_new_events()
                # Dovrebbe restituire lista vuota invece di crashare
                if isinstance(events, list) and len(events) == 0:
                    print("   ✅ Timeout gestito correttamente (lista vuota)")
                    return True
                else:
                    print(f"   ❌ Timeout non gestito: {events}")
                    return False
            except Exception as e:
                print(f"   ❌ Timeout causò eccezione: {e}")
                return False

    def test_memory_pressure_simulation(self):
        """Test comportamento sotto memory pressure."""
        print("\n🧪 Test Memory Pressure Simulation...")

        config = MagicMock()
        config.rules_path = "config/audit_rules.yaml"

        engine = AuditorEngine(config)
        engine.start()

        # Genera molti eventi per simulare memory pressure
        large_events = []
        for i in range(1000):
            large_events.append({
                "type": "tool",
                "tool_name": "FileEdit",
                "tool_input": {
                    "file_path": f"large_file_{i}.py",
                    "old_string": "",
                    "new_string": "x" * 10000  # 10KB per evento
                }
            })

        try:
            processed = 0
            for event in large_events:
                result = engine.analyze_event(event)
                processed += 1

            engine.stop()
            print(f"   ✅ Processati {processed} eventi large senza crash")
            return processed == len(large_events)

        except MemoryError:
            print("   ⚠️  MemoryError rilevato (atteso sotto memory pressure)")
            return True  # È accettabile un MemoryError sotto stress
        except Exception as e:
            print(f"   ❌ Errore inatteso: {e}")
            engine.stop()
            return False

    def test_concurrent_access_simulation(self):
        """Test accesso concorrente simulato."""
        print("\n🧪 Test Concurrent Access Simulation...")

        import threading

        config = MagicMock()
        config.rules_path = "config/audit_rules.yaml"

        engine = AuditorEngine(config)
        engine.start()

        results = []
        errors = []

        def worker_thread(thread_id):
            """Thread worker per test concorrenza."""
            try:
                for i in range(50):
                    event = {
                        "type": "tool",
                        "tool_name": "FileEdit",
                        "tool_input": {
                            "file_path": f"thread_{thread_id}_{i}.py",
                            "old_string": "",
                            "new_string": f"SECRET_{thread_id}_{i} = 'value'"
                        }
                    }
                    result = engine.analyze_event(event)
                    results.append(result)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Avvia 5 thread concorrenti
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker_thread, args=(i,))
            threads.append(t)
            t.start()

        # Aspetta completamento
        for t in threads:
            t.join()

        engine.stop()

        if errors:
            print(f"   ❌ Errori concorrenza: {len(errors)}")
            for error in errors[:3]:  # Mostra primi 3 errori
                print(f"      {error}")
            return False
        else:
            print(f"   ✅ Accesso concorrente riuscito: {len(results)} risultati")
            return len(results) == 250  # 5 thread * 50 eventi ciascuno

    def cleanup(self):
        """Pulizia ambiente test."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    """Esegue tutti i test di failure scenarios."""
    print("🚨 Auditor Agent - Failure Scenarios Test Suite")
    print("=" * 55)

    test_suite = TestFailureScenarios()

    try:
        tests = [
            ("Invalid Config File", test_suite.test_invalid_config_file),
            ("Missing Rules File", test_suite.test_missing_rules_file),
            ("HCom Connection Failure", test_suite.test_hcom_connection_failure),
            ("Corrupt Event Data", test_suite.test_corrupt_event_data),
            ("Network Timeout", test_suite.test_network_timeout_simulation),
            ("Memory Pressure", test_suite.test_memory_pressure_simulation),
            ("Concurrent Access", test_suite.test_concurrent_access_simulation),
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

        print("\n" + "=" * 55)
        print(f"📊 Risultati: {passed}/{total} test passati")

        if passed >= total * 0.8:  # 80% success rate per failure tests
            print("🎉 Failure scenarios gestiti adeguatamente!")
            return 0
        else:
            print("⚠️  Alcuni failure scenarios non gestiti correttamente.")
            return 1

    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    sys.exit(main())
