# Auditor Agent - Claude Code Companion 🤖🔍

Un agente di auditing intelligente che monitora e valida le azioni di Claude Code in tempo reale, fornendo un secondo livello di controllo qualità e sicurezza.

## Stato reale (auditabile)

- **IMPLEMENTATO (eseguibile)**:
  - Polling eventi via `hcom` (API Python se disponibile, altrimenti CLI) e invio messaggi/avvisi.
  - Motore di regole locale (`config/audit_rules.yaml`) + analisi base (regex/euristiche).
  - Dashboard TUI (thread separato, best-effort).
  - Test suite `python test_auditor.py` (passata in questo workspace).
- **PARZIALMENTE IMPLEMENTATO**:
  - Modalità `block`: oggi è un **soft-block** (messaggio “AUDIT BLOCK”), non un gate hard su tool execution.
- **NON IMPLEMENTATO (oggi solo roadmap)**:
  - Integrazione effettiva con `AI-Github-Auditor` e `python-a2a` (nel repository sono stati clonati a parte, ma non sono incorporati nel runtime del concept).
  - Gate hard (git hooks / pre-commit / policy engine).

## 🎯 Concept Overview

Questo progetto combina tecnologie open-source per creare un sistema di auditing multi-agente che lavora in parallelo con Claude Code:

- **Comunicazione**: `hcom` (repo `aannoo/claude-hook-comms`) per eventi/trascritti/messaging
- **Auditing Engine (attuale)**: regole locali + controlli base (pattern matching statico)
- **Roadmap**: innesto di scanner/policy engine MIT/Apache-2.0 + LLM integration

### ⚠️ **Limite Critico Attuale**

**Il sistema attuale NON è un "AI Auditor" completo**. È un "linting tool avanzato" che fa:

- ✅ Pattern matching statico (regex su hardcoded secrets, comandi pericolosi)
- ✅ Regole YAML configurabili
- ✅ Integrazione con Claude Code via hcom
- ❌ **NON** ragionamento semantico o analisi intelligente
- ❌ **NON** LLM per valutazione impatto e suggerimenti

**Per diventare un vero "AI Auditor" serve aggiungere LLM integration** (OpenAI GPT/Claude/etc.) per analisi intelligente del codice e contesto.

## 🏗️ Architettura

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude Code   │◄──►│ claude-hook-comms│◄──►│  Auditor Agent  │
│   (Primary)     │    │  (Communication) │    │   (Secondary)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                           │
                              ▼                           ▼
                       ┌──────────────────┐    ┌──────────────────┐
                       │   Event Stream   │    │  Audit Engine    │
                       │   (SQLite DB)    │    │  (AI Analysis)   │
                       └──────────────────┘    └──────────────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │   Validation     │
                                       │   & Alerts       │
                                       └──────────────────┘
```

## 🚀 Come Funziona

### 1. Setup Iniziale
```bash
# Clona il repository
git clone https://github.com/JoyciAkira/Auditor.git
cd Auditor

# Installa dipendenze
pip install -r requirements.txt

# Setup automatico
python setup.py

# Installa claude-hook-comms
pip install hcom
hcom

# Configura hooks per Claude Code
# (segui istruzioni in docs/quick_start.md)
```

### 2. Avvia l'Auditor
```bash
# Terminale 1: Claude Code normale
claude

# Terminale 2: Auditor Agent
python auditor_agent/main.py --mode warn --dashboard
```

### 3. Workflow Operativo
1. **Claude Code** lavora normalmente sul progetto
2. **Hook System** intercetta ogni azione (file edits, tool calls, commits)
3. **Auditor Agent** riceve notifiche in tempo reale via claude-hook-comms
4. **Audit Engine** valida:
   - Sicurezza del codice
   - Qualità e best practices
   - Conformità ai requisiti
   - Rilevamento regressioni
5. **Alert System** notifica l'utente se rileva problemi

## 📁 Struttura Progetto

```
auditor-concept/
├── auditor_agent/           # Core dell'agente auditor
│   ├── main.py             # Entry point
│   └── main.py             # Loop + routing eventi + invio messaggi
├── communication_layer/    # Integrazione con claude-hook-comms
│   ├── hcom_client.py      # Client per hcom
├── audit_engine/          # Engine di analisi (basato su AI-Github-Auditor)
│   └── auditor.py         # Regole + analisi base
├── monitoring/            # Sistema di monitoraggio
│   ├── dashboard.py       # Dashboard semplice
├── config/                # Configurazioni
│   ├── audit_rules.yaml   # Regole di auditing
│   ├── agent_config.py    # Loader config (IMPLEMENTATO)
│   └── agent_config.yaml  # Config agente
└── docs/                  # Documentazione
    └── quick_start.md     # Quick start
```

## 🔧 Configurazione

### Regole di Auditing (config/audit_rules.yaml)
```yaml
security:
  - name: "hardcoded_secrets"
    pattern: "(?i)(password|secret|key|token).*['\"]([^'\"]*)['\"]"
    severity: "high"
    action: "block"

quality:
  - name: "large_functions"
    max_lines: 50
    severity: "medium"
    action: "warn"

compliance:
  - name: "missing_tests"
    require_tests: true
    severity: "low"
    action: "suggest"
```

### Modalità Operative
- **Read-only**: Solo monitoraggio e suggerimenti
- **Warn**: Notifiche per problemi rilevati
- **Block**: Blocco automatico di azioni rischiose
- **Interactive**: Richiesta conferma per azioni critiche

## 🛠️ Setup Rapido

1. **Installa dipendenze**:
```bash
pip install -r requirements.txt
```

2. **Configura hooks**: vedi `docs/quick_start.md` (usa snippet ufficiale di `claude-hook-comms`)

3. **Avvia sistema**:
```bash
# Terminale 1
claude

# Terminale 2
python auditor_agent/main.py
```

## 🎯 Casi d'Uso

### Sicurezza
- Rilevamento chiavi API hardcodate
- Validazione input non sicura
- Controlli dipendenze vulnerabili

### Qualità Codice
- Complessità ciclomatica
- Coverage test
- Best practices linguaggio

### Compliance
- Conformità standard aziendali
- Validazione architetturale
- Controlli regressione

### Workflow
- Code review automatizzato
- Validazione pre-commit
- Monitoraggio modifiche critiche

## 🔄 Integrazione con Claude Code

L'agente si integra perfettamente con Claude Code attraverso:

1. **Hooks di sistema**: Intercetta tool calls e file edits
2. **Event streaming**: Riceve notifiche in tempo reale
3. **Message passing**: Può inviare suggerimenti e avvisi
4. **Transcript access**: Legge conversazioni per context awareness

## 🤖 Aggiungere LLM Integration (per diventare "AI Auditor")

Per trasformare questo da "linting tool" a "AI Auditor" vero, aggiungere:

### 1. Dipendenze LLM
```bash
pip install openai anthropic  # O altri provider
```

### 2. Configurazione
```yaml
# config/agent_config.yaml
llm:
  provider: "openai"  # openai, anthropic, local
  model: "gpt-4"
  api_key: "${OPENAI_API_KEY}"
  temperature: 0.1
  max_tokens: 1000
```

### 3. Engine AI
```python
# audit_engine/ai_analyzer.py
import openai

class AIAnalyzer:
    def analyze_code_change(self, code_diff: str, context: dict) -> dict:
        """Analizza cambiamenti codice con LLM per impatto/risk assessment"""
        prompt = f"""
        Analizza questo cambiamento codice per rischi di sicurezza e qualità:

        {code_diff}

        Contesto: {context}

        Fornisci:
        - Livello di rischio (low/medium/high)
        - Problemi potenziali
        - Suggerimenti miglioramento
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        return self.parse_llm_response(response)
```

## 🚀 Estensioni Future

- **LLM Integration** (vedi sopra) per analisi intelligente
- Integrazione con git hooks per validazione pre-commit
- Dashboard web per monitoraggio real-time
- Plugin system per regole custom
- Integrazione con CI/CD pipelines
- Multi-agent orchestration con python-a2a

## Miglioramenti ambiziosi (con sorgenti MIT/Apache-2.0 verificati)

Questi componenti sono stati verificati via GitHub API (campo `license.spdx_id`) nel workspace corrente:

- **Secret scanning hard**:
  - `gitleaks/gitleaks` (**MIT**) – secrets in repo e history
  - `Yelp/detect-secrets` (**Apache-2.0**) – baseline enterprise-friendly
  - `aquasecurity/trivy` (**Apache-2.0**) – vulnerabilità + misconfig + secrets + SBOM
- **SAST / sicurezza**:
  - `PyCQA/bandit` (**Apache-2.0**) – security lint Python
  - `bridgecrewio/checkov` (**Apache-2.0**) – IaC scanning (Terraform/K8s/etc.)
  - `rhysd/actionlint` (**MIT**) – lint workflow GitHub Actions
- **Gate deterministico**:
  - `pre-commit/pre-commit` (**MIT**) – framework per hook; consente gating locale prima del commit
  - `open-policy-agent/opa` (**Apache-2.0**) – policy engine (rego) per decisioni “allow/deny” tracciabili

Integrazione concreta suggerita (non implementata in questo concept): aggiungere uno strato “policy gate” che, prima di `git commit`/`git push` o prima di tool execution, esegue gli scanner sopra e produce una decisione `allow|deny` con evidenza.

## 📊 Metriche e Reporting

L'agente traccia:
- Tasso di problemi rilevati vs risolti
- Tempo di risposta alle notifiche
- Accuratezza delle rilevazioni
- Impatto sulla produttività

## 🤝 Contributi

Questo è un concept basato su progetti open-source esistenti. Per contribuire:

1. Fork dei repository originali
2. Implementa miglioramenti specifici
3. Crea PR nei progetti upstream
4. Documenta integrazioni nuove

---

**Basato su**: claude-hook-comms, AI-Github-Auditor, python-a2a
**Licenza**: MIT
**Status**: Concept funzionante
