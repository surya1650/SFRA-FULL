#!/usr/bin/env python3
"""Seed the ``combination`` table from ``standards/ieee_c57_149_combinations.yaml``.

Idempotent: re-running upserts (no duplicates, no orphan deletes). Safe to
run on every container start so a fresh deployment automatically picks up
catalogue edits without manual intervention.

Usage:
    python3 scripts/seed_combinations.py
    SFRA_DATABASE_URL=sqlite:///data/app.db python3 scripts/seed_combinations.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml
from sqlalchemy import select

# Make src/ importable when run as a bare script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sfra_full.db import (  # noqa: E402
    Base,
    Combination,
    TransformerType,
    build_engine,
    build_sessionmaker,
)


CATALOGUE_PATH = ROOT / "standards" / "ieee_c57_149_combinations.yaml"


def seed(database_url: str | None = None) -> int:
    """Upsert the combinations from the YAML catalogue.

    Returns the number of rows now present in the table.
    """
    engine = build_engine(database_url)
    Base.metadata.create_all(engine, tables=[Combination.__table__])
    Session = build_sessionmaker(engine)

    with CATALOGUE_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    inserted = 0
    updated = 0
    with Session() as session:
        for ttype_str, spec in (data.get("transformer_types", {}) or {}).items():
            ttype = TransformerType(ttype_str)
            for row in spec.get("combinations") or []:
                existing = session.scalar(
                    select(Combination).where(
                        Combination.transformer_type == ttype,
                        Combination.code == row["code"],
                    )
                )
                payload = {
                    "transformer_type": ttype,
                    "code": row["code"],
                    "sequence": int(row["sequence"]),
                    "category": row["category"],
                    "winding": row["winding"],
                    "phase": row["phase"],
                    "injection_terminal": row["injection_terminal"],
                    "measurement_terminal": row["measurement_terminal"],
                    "shorted_terminals": list(row.get("shorted_terminals") or []),
                    "grounded_terminals": list(row.get("grounded_terminals") or []),
                    "description": row.get("description"),
                }
                if existing is None:
                    session.add(Combination(**payload))
                    inserted += 1
                else:
                    for k, v in payload.items():
                        setattr(existing, k, v)
                    updated += 1
        session.commit()
        total = session.scalar(select(Combination).with_only_columns(
            Combination.id  # type: ignore[arg-type]
        ).order_by(Combination.id.desc()).limit(1))

    print(
        f"[seed_combinations] inserted={inserted} updated={updated} "
        f"max_id={total or 0} database={engine.url}"
    )
    return inserted + updated


if __name__ == "__main__":
    seed()
