#!/usr/bin/env python3
"""
Script di setup per Auditor Agent.
Installa dipendenze e configura l'ambiente.
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd, description):
    """Esegue un comando e gestisce gli errori."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True,
                              capture_output=True, text=True)
        print(f"✅ {description} completato")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore in {description}: {e}")
        print(f"Output: {e.output}")
        return False


def check_python_version():
    """Verifica la versione Python."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ richiesto")
        return False
    print(f"✅ Python {sys.version.split()[0]} rilevato")
    return True


def install_dependencies():
    """Installa le dipendenze necessarie."""
    dependencies = [
        "hcom",               # claude-hook-comms su PyPI
        "pyyaml",             # Per configurazione YAML
        "rich",               # Per dashboard
        "requests",           # Per API calls
    ]

    success = True
    for dep in dependencies:
        if not run_command(f"pip install {dep}", f"Installazione {dep}"):
            success = False

    return success


def setup_directories():
    """Crea le directory necessarie."""
    directories = [
        "logs",
        "cache",
        "reports"
    ]

    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"📁 Directory {dir_name} creata")

    return True


def setup_hcom():
    """Configura claude-hook-comms."""
    print("🔗 Configurazione claude-hook-comms...")

    # Verifica se hcom è disponibile
    try:
        result = subprocess.run(["hcom", "--help"],
                              capture_output=True, timeout=10)
        if result.returncode == 0:
            print("✅ hcom già installato")

            # Inizializza hcom se necessario
            try:
                subprocess.run(["hcom", "list"], capture_output=True, timeout=5)
            except subprocess.CalledProcessError:
                print("🔧 Inizializzazione hcom...")
                subprocess.run(["hcom"], timeout=10)

            return True
        else:
            print("❌ hcom non funzionante")
            return False

    except FileNotFoundError:
        print("❌ hcom non installato. Installa con: pip install hcom")
        return False
    except Exception as e:
        print(f"❌ Errore configurazione hcom: {e}")
        return False


def create_env_file():
    """Crea file .env di esempio."""
    env_content = """# Configurazione Auditor Agent
# Copia questo file come .env e configura i valori necessari

# GitHub (opzionale, per analisi repository avanzate)
# GITHUB_TOKEN=your_github_token_here

# OpenAI (opzionale, per analisi AI avanzate)
# OPENAI_API_KEY=your_openai_key_here

# Slack webhook (opzionale, per notifiche)
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Configurazione database hcom
# HCOM_DB_PATH=~/.hcom/db.sqlite

# Log level
# LOG_LEVEL=INFO
"""

    env_file = Path(".env.example")
    if not env_file.exists():
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("📄 File .env.example creato")
        print("   Copialo come .env e configura le variabili necessarie")

    return True


def main():
    """Funzione principale di setup."""
    print("🚀 Setup Auditor Agent")
    print("=" * 50)

    # Verifica Python
    if not check_python_version():
        sys.exit(1)

    # Installa dipendenze
    if not install_dependencies():
        print("❌ Installazione dipendenze fallita")
        sys.exit(1)

    # Setup directory
    if not setup_directories():
        print("❌ Creazione directory fallita")
        sys.exit(1)

    # Setup hcom
    if not setup_hcom():
        print("⚠️  hcom non configurato. Alcune funzionalità potrebbero non essere disponibili.")
        print("   Installa manualmente con: pip install hcom && hcom")

    # Crea file env
    create_env_file()

    print("\n" + "=" * 50)
    print("✅ Setup completato!")
    print("\n📋 Prossimi passi:")
    print("1. Copia .env.example come .env e configura le variabili")
    print("2. Assicurati che Claude Code sia configurato con gli hook")
    print("3. Avvia l'agente con: python auditor_agent/main.py")
    print("\n📚 Documentazione: vedi README.md")


if __name__ == "__main__":
    main()
