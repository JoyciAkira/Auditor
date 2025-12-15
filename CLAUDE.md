# CLAUDE.md — Project instructions for Claude Code

Questo file fornisce **contesto persistente** e **convenzioni operative** per lavorare su questo repository con Claude Code.
Riferimento ufficiale su CLAUDE.md e `/init`: `https://claude.com/blog/using-claude-md-files`.

## Scopo

- Ridurre ambiguità: stack, struttura, entrypoint, comandi tipici.
- Definire regole non negoziabili (sicurezza, stile, workflow).
- Fornire istruzioni che valgono per tutto il team, in ogni sessione Claude Code.

## Repository overview

Questo repo contiene un concept chiamato **Auditor**:
- Un processo Python che monitora eventi (via `hcom`) e applica regole deterministiche (pattern matching) + analisi AI opzionale (Ollama/CodeGeeX).

### Componenti principali (cartelle)

- `auditor_agent/`: entrypoint runtime dell’agente auditor.
- `audit_engine/`: motore di regole + integrazione AI (Ollama).
- `communication_layer/`: integrazione con `claude-hook-comms` (`hcom`).
- `config/`: configurazione YAML (agente + regole).
- `docs/`: documentazione e changelog.

## Comandi (documentati, non auto-eseguiti)

Nota: non eseguire comandi di build/lint/test se non richiesto esplicitamente dall’utente o dalla spec corrente.

### Setup

Da repo root:
- Install: `pip install -r requirements.txt`
- Test base: `python test_auditor.py`
- Avvio agent: `python auditor_agent/main.py --mode warn --dashboard`

### AI locale (Ollama)

- Endpoint Ollama: configurabile in `config/agent_config.yaml`
- Modello target tipico: `codegeex4:latest`

## Regole di progetto (non negoziabili)

### Linguaggio e comunicazione

- Tutti i messaggi, output e documentazione **in italiano tecnico**.
- Nessun linguaggio condizionale (“dovrebbe”, “probabilmente”) quando si descrive lo stato del sistema.
- Distinguere sempre: **implementato**, **parzialmente implementato**, **non implementato**.
- Ogni affermazione deve derivare da **codice reale**, **output verificabile**, o **documentazione ufficiale**.

### Sicurezza

- Non introdurre segreti: chiavi, token, password, connection string.
- Evitare pattern insicuri: `eval()`, `exec()`, concatenazione SQL non parametrizzata.
- Non “fixare” disabilitando dipendenze o bypassando controlli: isolare e correggere la causa.

### Qualità e manutenibilità

- Soluzioni minime e modulari: aggiungere solo ciò che serve per la feature richiesta.
- Error handling: non usare `except: pass` o catch generici che ingoiano errori.
- Commenti: spiegare **perché**, non “cosa”.

### Documentazione e tracciabilità

- Ogni modifica significativa richiede aggiornamenti coerenti in `docs/` (es. `CHANGELOG.md`).
- Dopo un ciclo completo: **git commit** e **git push** con messaggi chiari e auditabili.

## Workflow consigliato in Claude Code

1. Leggere la spec e chiarire ambiguità prima di scrivere codice.
2. Pianificare micro-task verificabili.
3. Implementare in piccoli incrementi, mantenendo il repo in stato consistente.
4. Aggiornare documentazione correlata.
5. Dimostrare con test reali (non mock) le funzionalità richieste quando la spec lo impone.

## Note su `/init`

Il comando `/init` di Claude Code genera un `CLAUDE.md` iniziale analizzando il progetto.
Questo file è mantenuto manualmente per riflettere lo stato reale del repository e le convenzioni del team.


