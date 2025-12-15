# 🚀 Quick Start - Auditor Agent

Guida rapida per configurare e utilizzare l'Auditor Agent con Claude Code.

## 📋 Prerequisiti

- Python 3.8+
- Claude Code installato
- Terminale con supporto ANSI (raccomandato)

## ⚡ Installazione Rapida

### 1. Setup Ambiente
```bash
# Clona il progetto
cd /Volumes/Partition_1/Auditor
git clone <repository-url> auditor-concept
cd auditor-concept

# Esegui setup automatico
python setup.py
```

### 2. Configura claude-hook-comms
```bash
# Installa hcom (se non già fatto dal setup)
pip install hcom

# Inizializza hcom
hcom

# Verifica funzionamento
hcom list
```

### 3. Configura Claude Code
Aggiungi gli hook al tuo `.claude/settings.json`.

Nota deterministica: il file di esempio qui sotto in precedenza era **incompleto** (JSON non valido). Inoltre, l’elenco “corretto” degli hook dipende dalla versione di `hcom` e dal tuo setup.
Per evitare configurazioni inventate, usa lo snippet **ufficiale** dal README di `claude-hook-comms` (repo `aannoo/claude-hook-comms`, sezione “hooks”) e applicalo al tuo progetto.

```json
{
  "hooks": {
    "SessionStart": [{"hooks": [{"type": "command", "command": "hcom sessionstart"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "hcom userpromptsubmit"}]}],
    "PreToolUse": [{"matcher": "Bash|Task", "hooks": [{"type": "command", "command": "hcom pre"}]}],
    "PostToolUse": [{"hooks": [{"type": "command", "command": "hcom post", "timeout": 86400}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "hcom poll", "timeout": 86400}]}],
    "SubagentStart": [{"hooks": [{"type": "command", "command": "hcom subagent-start"}]}],
    "SubagentStop": [{"hooks": [{"type": "command", "command": "hcom subagent-stop", "timeout": 86400}]}],
    "Notification": [{"hooks": [{"type": "command", "command": "hcom notify"}]}],
    "SessionEnd": [{"hooks": [{"type": "command", "command": "hcom sessionend"}]}]
  },
  "env": {"HCOM": "hcom"}
}
```

### 4. Opt-in hcom nella sessione Claude
`hcom` blocca l’invio messaggi da “istanze vanilla Claude” finché non fai opt-in:

```bash
# dentro la sessione di Claude Code
hcom start
```

## 🎯 Utilizzo

### Avvio Base
```bash
# Terminale 1: Claude Code normale
claude

# Terminale 2: Auditor Agent
python auditor_agent/main.py --mode warn --dashboard
```

### Modalità Disponibili

| Modalità | Descrizione | Quando Usarla |
|----------|-------------|---------------|
| `readonly` | Solo monitoraggio, no azioni | Per test iniziali |
| `warn` | Invia avvisi ma permette esecuzione | Ambiente di sviluppo |
| `block` | Blocca automaticamente azioni rischiose | Ambiente di produzione |

### Opzioni Avanzate
```bash
# Monitora solo un'istanza specifica
python auditor_agent/main.py --target alice

# Output verboso per debugging
python auditor_agent/main.py --verbose

# Configurazione custom
python auditor_agent/main.py --config my_config.yaml
```

## 🧪 Test del Sistema

```bash
# Esegui test automatici
python test_auditor.py

# Test manuale: in Claude Code esegui
run echo "Test funzionamento hooks"
```

## 📊 Dashboard

Quando abilitata (`--dashboard`), mostra:
- 📈 Statistiche in tempo reale
- 🔍 Problemi rilevati
- ⚡ Stato delle istanze
- 📋 Attività recente

## 🔧 Configurazione

### File Configurazione
Modifica `config/agent_config.yaml`:

```yaml
agent:
  name: "auditor"
  mode: "warn"  # readonly, warn, block
  enable_dashboard: true

auditing:
  rules_path: "config/audit_rules.yaml"
  enable_security_checks: true
  enable_quality_checks: true
```

### Regole Custom
Aggiungi regole in `config/audit_rules.yaml`:

```yaml
security:
  - name: "my_custom_rule"
    pattern: "regex pattern"
    severity: "high"
    action: "block"
    description: "Mia regola personalizzata"
```

## 🚨 Cosa Rileva

### Sicurezza
- ❌ Segreti hardcodati
- ❌ Comandi pericolosi (`rm -rf /`)
- ❌ SQL injection risks
- ❌ Permessi eccessivi

### Qualità
- ⚠️ Funzioni troppo lunghe
- 💡 Error handling mancante
- 📝 Import inutilizzati

### Workflow
- 🚨 Operazioni critiche (push, deploy)
- 💭 Commit senza test
- 📊 Migrazioni database

## 🔄 Ciclo Operativo

1. **Claude Code** lavora normalmente
2. **Hook System** intercetta ogni azione
3. **Auditor Agent** analizza in tempo reale
4. **Alert/Block** se necessario
5. **Report** delle attività

## 🛠 Troubleshooting

### Problema: hcom non trovato
```bash
pip install hcom
hcom  # Inizializza
```

### Problema: Hook non funzionanti
- Verifica `.claude/settings.json`
- Riavvia Claude Code
- Controlla `hcom events`

### Problema: Audit non rileva problemi
```bash
python test_auditor.py  # Verifica regole
python auditor_agent/main.py --verbose  # Debug
```

## 📈 Esempi d'Uso

### Sviluppo Sicuro
```bash
# Ambiente sviluppo con avvisi
python auditor_agent/main.py --mode warn --dashboard
```

### Produzione Protetta
```bash
# Ambiente produzione con blocchi
python auditor_agent/main.py --mode block --config prod_config.yaml
```

### Debug Specifico
```bash
# Monitora solo istanza specifica
python auditor_agent/main.py --target dev-instance --verbose
```

---

**Pronto?** Avvia con `python auditor_agent/main.py` e inizia a sviluppare in sicurezza! 🛡️
