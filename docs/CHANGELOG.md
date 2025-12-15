# Changelog (auditabile)

Questo file registra modifiche significative al concept, con focus su riproducibilità e tracciabilità.

## 2025-12-15

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


