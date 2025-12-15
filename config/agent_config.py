"""
Caricamento configurazione Auditor Agent.

Stato: IMPLEMENTATO (minimale).
Limiti:
- Valida solo campi essenziali.
- Non applica schema/typing rigorosi (manca pydantic o simili).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class AgentConfig:
    # Agent
    agent_name: str = "auditor"
    mode: str = "warn"  # readonly|warn|block
    target_instance: Optional[str] = None
    enable_dashboard: bool = True
    verbose: bool = False

    # Auditing
    rules_path: str = "config/audit_rules.yaml"

    @classmethod
    def from_file(cls, config_path: str | Path | None) -> "AgentConfig":
        if not config_path:
            return cls()

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config non trovata: {path}")

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        agent = data.get("agent", {}) or {}
        auditing = data.get("auditing", {}) or {}

        return cls(
            agent_name=str(agent.get("name", "auditor")),
            mode=str(agent.get("mode", "warn")),
            target_instance=agent.get("target_instance", None),
            enable_dashboard=bool(agent.get("enable_dashboard", True)),
            verbose=bool(agent.get("verbose", False)),
            rules_path=str(auditing.get("rules_path", "config/audit_rules.yaml")),
        )

    def __init__(self, config_path: str | Path | None = None, **overrides: Any):
        cfg = self.from_file(config_path) if config_path else None
        if cfg:
            self.agent_name = cfg.agent_name
            self.mode = cfg.mode
            self.target_instance = cfg.target_instance
            self.enable_dashboard = cfg.enable_dashboard
            self.verbose = cfg.verbose
            self.rules_path = cfg.rules_path
        # Override da kwargs
        for k, v in overrides.items():
            if hasattr(self, k):
                setattr(self, k, v)


