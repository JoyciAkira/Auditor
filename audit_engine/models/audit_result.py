"""
Modelli di dati per i risultati dell'auditing.
Separati per evitare import circolari.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AuditResult:
    """Risultato di un'analisi di audit."""
    rule_name: str
    severity: str
    action: str
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    evidence: Optional[str] = None
