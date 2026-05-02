"""DB layer integration tests — schema build, array round-trip, FK enforcement."""
from __future__ import annotations

from datetime import date

import numpy as np
import pytest
from sqlalchemy import select

from sfra_full.db import (
    Base,
    Combination,
    InterventionType,
    OverhaulCycle,
    SessionType,
    SourceFormat,
    TestSession,
    Trace,
    TraceRole,
    Transformer,
    TransformerType,
    build_engine,
    build_sessionmaker,
)
from sfra_full.db.array_helpers import array_pair_roundtrip, array_to_bytes


@pytest.fixture()
def session():
    engine = build_engine("sqlite://")
    Base.metadata.create_all(engine)
    Sm = build_sessionmaker(engine)
    with Sm() as s:
        yield s


def test_all_tables_build():
    # Importing auth.models registers the user table on Base.metadata.
    from sfra_full.auth.models import User  # noqa: F401

    engine = build_engine("sqlite://")
    Base.metadata.create_all(engine)
    table_names = sorted(Base.metadata.tables.keys())
    assert table_names == [
        "analysis_result",
        "combination",
        "overhaul_cycle",
        "test_session",
        "trace",
        "transformer",
        "user",
    ]


def test_array_roundtrip_bit_exact():
    arr = np.logspace(1, 6, 1500, dtype=np.float64)
    assert array_pair_roundtrip(arr)


def test_transformer_unique_serial(session):
    session.add(Transformer(serial_no="X1", transformer_type=TransformerType.TWO_WINDING))
    session.commit()
    session.add(Transformer(serial_no="X1", transformer_type=TransformerType.TWO_WINDING))
    with pytest.raises(Exception):
        session.commit()
    session.rollback()


def test_full_relationship_chain(session):
    """Transformer → OverhaulCycle → TestSession → Trace round-trip."""
    t = Transformer(
        serial_no="TR-FOO",
        transformer_type=TransformerType.TWO_WINDING,
        nameplate_mva=100.0,
    )
    session.add(t)
    session.flush()

    cycle = OverhaulCycle(
        transformer_id=t.id,
        cycle_no=1,
        cycle_start_date=date(2026, 4, 1),
        intervention_type=InterventionType.COMMISSIONING,
    )
    session.add(cycle)
    session.flush()

    ts = TestSession(
        transformer_id=t.id,
        overhaul_cycle_id=cycle.id,
        session_type=SessionType.COMMISSIONING,
        session_date=date(2026, 4, 15),
    )
    session.add(ts)
    session.flush()

    f = np.logspace(1, 6, 800)
    m = -20 - 10 * np.log10(f)
    p = -90 + 0 * f
    trace = Trace(
        test_session_id=ts.id,
        role=TraceRole.TESTED,
        label="HV-end-to-end",
        source_file_format=SourceFormat.FRAX,
        frequency_hz=array_to_bytes(f),
        magnitude_db=array_to_bytes(m),
        phase_deg=array_to_bytes(p),
        point_count=int(f.size),
        freq_min_hz=float(f.min()),
        freq_max_hz=float(f.max()),
    )
    session.add(trace)
    session.commit()

    fetched = session.scalar(select(Transformer).where(Transformer.serial_no == "TR-FOO"))
    assert fetched is not None
    assert len(fetched.overhaul_cycles) == 1
    assert fetched.overhaul_cycles[0].is_open is True
    assert len(fetched.test_sessions) == 1
    assert len(fetched.test_sessions[0].traces) == 1


def test_seed_combinations(tmp_path, monkeypatch):
    """The seeder upserts the YAML catalogue into the combination table."""
    db_url = f"sqlite:///{tmp_path}/seed.db"
    monkeypatch.setenv("SFRA_DATABASE_URL", db_url)

    from scripts import seed_combinations  # type: ignore[import-not-found]

    n = seed_combinations.seed(db_url)
    assert n == 84  # 15 + 21 + 12 + 36

    engine = build_engine(db_url)
    Sm = build_sessionmaker(engine)
    with Sm() as s:
        codes = sorted(
            r.code for r in s.scalars(
                select(Combination).where(
                    Combination.transformer_type == TransformerType.TWO_WINDING
                )
            )
        )
    assert "EEOC_HV_R" in codes
    assert "EESC_HV_R" in codes
    assert "IIW_HV_LV_T" in codes
    assert len(codes) == 15
