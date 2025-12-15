#!/usr/bin/env python3
"""
Test script per Auditor Agent.
Simula eventi e verifica il funzionamento del sistema.
"""

import sys
import time
import json
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

from audit_engine.auditor import AuditorEngine, AuditResult
from config.agent_config import AgentConfig


class MockConfig:
    """Configurazione mock per test."""
    def __init__(self):
        self.mode = "warn"
        self.verbose = True
        self.rules_path = "config/audit_rules.yaml"
        self.enable_dashboard = False


def test_audit_engine():
    """Test del motore di auditing."""
    print("🧪 Test Audit Engine...")

    config = MockConfig()
    engine = AuditorEngine(config)
    engine.start()

    # Test eventi simulati
    test_events = [
        # Evento tool con comando pericoloso
        {
            "type": "tool",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /tmp/test"}
        },

        # Evento tool con modifica file sicura
        {
            "type": "tool",
            "tool_name": "FileEdit",
            "tool_input": {
                "file_path": "test.py",
                "old_string": "",
                "new_string": "print('hello world')"
            }
        },

        # Evento tool con hardcoded secret
        {
            "type": "tool",
            "tool_name": "FileEdit",
            "tool_input": {
                "file_path": "config.py",
                "old_string": "",
                "new_string": "API_KEY = 'sk-1234567890abcdef'"
            }
        },

        # Evento status commit
        {
            "type": "status",
            "status_detail": "commit: Add new feature"
        }
    ]

    results = []
    for i, event in enumerate(test_events, 1):
        print(f"\n📝 Test {i}: {event['type']} - {event.get('tool_name', 'N/A')}")
        result = engine.analyze_event(event)
        if result:
            print(f"   ✅ Rilevato: {result.rule_name} ({result.severity}) - {result.action}")
            print(f"   💡 Suggerimento: {result.suggestion}")
            results.append(result)
        else:
            print("   ⚪ Nessun problema rilevato")

    engine.stop()

    print(f"\n📊 Risultati test: {len(results)} problemi rilevati su {len(test_events)} eventi")
    return len(results) > 0


def test_config_loading():
    """Test caricamento configurazione."""
    print("\n🧪 Test Config Loading...")

    try:
        config = AgentConfig("config/agent_config.yaml")
        print("✅ Configurazione caricata correttamente")
        print(f"   Mode: {config.mode}")
        print(f"   Agent name: {config.agent_name}")
        return True
    except Exception as e:
        print(f"❌ Errore caricamento config: {e}")
        return False


def simulate_integration_test():
    """Test simulato di integrazione con hcom."""
    print("\n🧪 Test Integrazione HCom (simulato)...")

    # Simula risposta hcom list
    mock_hcom_response = [
        {"name": "alice", "status": "active", "directory": "/home/user/project"},
        {"name": "auditor", "status": "active", "directory": "/home/user/project"}
    ]

    print("✅ Connessione hcom simulata")
    print(f"   Istanze rilevate: {len(mock_hcom_response)}")

    for instance in mock_hcom_response:
        print(f"   👤 {instance['name']}: {instance['status']}")

    return True


def main():
    """Funzione principale di test."""
    print("🚀 Auditor Agent - Test Suite")
    print("=" * 40)

    tests = [
        ("Config Loading", test_config_loading),
        ("Audit Engine", test_audit_engine),
        ("HCom Integration", simulate_integration_test),
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

    print("\n" + "=" * 40)
    print(f"📊 Risultati: {passed}/{total} test passati")

    if passed == total:
        print("🎉 Tutti i test passati! Auditor Agent pronto per l'uso.")
        return 0
    else:
        print("⚠️  Alcuni test falliti. Controlla la configurazione.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
