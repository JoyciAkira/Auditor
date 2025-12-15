# Changelog (auditabile)

Questo file registra modifiche significative al concept, con focus su riproducibilità e tracciabilità.

## 2025-12-15

### Repository Pubblico 🚀
- **Creato repository GitHub pubblico**: https://github.com/JoyciAkira/Auditor
- **Push iniziale**: codice e documentazione completamente funzionanti
- **Aggiornamento docs**: istruzioni clone corrette per repository pubblico

### ⚠️ **Correzione Status: Pattern-Based (Non AI)**
- **Precisazione**: il sistema attuale è "linting tool avanzato" con pattern matching statico
- **Limite identificato**: manca LLM integration per ragionamento semantico e analisi intelligente
- **Documentazione aggiornata**: chiarito che serve LLM per diventare "AI Auditor" completo

### Fix / Coerenza contratti
- Corretto `test_auditor.py`: rimosso `SyntaxError` e ripristinata esecuzione test.
- Allineato `communication_layer/hcom_client.py` al contratto reale di `hcom`:
  - rimosso uso di flag non supportati (`--to` su CLI)
  - evitata assunzione errata su formato JSON di `hcom events` (JSON per riga; nessun `id`)
  - introdotta deduplica locale tramite fingerprint.

### Eseguibilità
- Implementato `config/agent_config.py` (loader YAML minimale) per rendere avvio/test deterministici.
- Resa coerente la pipeline `AuditResult` (stats aggiornate dentro `AuditorEngine`).
- Fix `setup.py` e `requirements.txt`: package corretto su PyPI è `hcom`.

### Documentazione
- Aggiornati `README.md` e `docs/quick_start.md` per riflettere lo stato reale: implementato vs parziale vs non implementato.

### 🤖 AI Integration (Ollama/CodeGeeX)
- **Implementato**: Client Ollama completo con timeout configurabili
- **Testato**: Connessione funzionante a `192.168.1.251:11434` (tuo NAS)
- **Validato**: CodeGeeX 9B risponde (~33s con prompt vincolato)
- **Cold-start handling**: Timeout 180s+ per modello 9B su hardware NAS
- **Architettura**: Sistema ibrido (pattern matching veloce → AI profonda per casi complessi)


