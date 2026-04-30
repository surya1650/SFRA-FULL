"""Command-line entry point for the APTRANSCO SFRA platform.

Phase 0 commands:

    sfra-full analyse <tested> [--reference <path>] [--out <json>]
        Run the analysis runner. With ``--reference`` it does Mode 1
        (comparative); without, Mode 2 (single-trace). Result is dumped
        as JSON to ``--out`` or stdout.

    sfra-full frax-info <path>
        List the sweeps inside a FRAX file with resolved combination_code.

    sfra-full validate-catalogue
        Re-run the YAML schema validator (same as ``make validate-catalogue``).

    sfra-full version
        Print the engine version.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .sfra_analysis.io import parse_file
from .sfra_analysis.result_types import TraceData
from .sfra_analysis.runner import run


def _load_first_sweep(path: str) -> TraceData:
    fmt, sweeps = parse_file(path)
    if not sweeps:
        raise SystemExit(f"No sweeps found in {path}")
    s = sweeps[0]
    return TraceData(
        frequency_hz=s.frequency_hz,
        magnitude_db=s.magnitude_db,
        phase_deg=s.phase_deg,
        label=s.label,
        metadata={
            "source_format": s.source_format,
            "source_file": s.source_file,
            "combination_code": s.combination_code,
        },
    )


def _cmd_analyse(args: argparse.Namespace) -> int:
    tested = _load_first_sweep(args.tested)
    reference = _load_first_sweep(args.reference) if args.reference else None

    outcome = run(
        tested,
        reference=reference,
        transformer_type=args.transformer_type,
        combination_code=args.combination_code,
    )
    payload = outcome.to_dict()

    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(json.dumps(payload, indent=2))
    return 0


def _cmd_frax_info(args: argparse.Namespace) -> int:
    fmt, sweeps = parse_file(args.path)
    print(f"Format: {fmt}    Sweeps: {len(sweeps)}")
    print(f"{'#':>3}  {'Combo':22s} {'Phase':5s} {'Wnd':4s} {'Test':18s} {'Pts':>5s}  Label")
    print("-" * 90)
    for i, s in enumerate(sweeps, 1):
        props = s.properties or {}
        print(
            f"{i:>3}  {str(s.combination_code or '<unmapped>'):22s} "
            f"{(props.get('Phase') or '-'):5s} "
            f"{(props.get('Winding') or '-'):4s} "
            f"{(props.get('Test') or '-'):18s} "
            f"{s.frequency_hz.size:>5d}  "
            f"{s.label}"
        )
    return 0


def _cmd_validate_catalogue(args: argparse.Namespace) -> int:
    # Re-import the validator script so its main() runs in this process.
    here = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(here / "scripts"))
    import validate_catalogue  # type: ignore[import-not-found]
    return int(validate_catalogue.main())


def _cmd_version(args: argparse.Namespace) -> int:
    print(f"sfra-full {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sfra-full",
        description="APTRANSCO SFRA Diagnostic Tool — CLI",
    )
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyse", help="Run analysis on a tested trace (Mode 1 or Mode 2).")
    a.add_argument("tested", help="Path to the tested trace (CSV / FRAX / XML)")
    a.add_argument("--reference", help="Optional reference trace path (Mode 1)")
    a.add_argument("--out", help="Path to write JSON output (default: stdout)")
    a.add_argument("--transformer-type", help="e.g. TWO_WINDING, AUTO_WITH_TERTIARY_BROUGHT_OUT")
    a.add_argument("--combination-code", help="e.g. EEOC_HV_R")
    a.set_defaults(func=_cmd_analyse)

    f = sub.add_parser("frax-info", help="List sweeps in a FRAX file with resolved combination codes.")
    f.add_argument("path", help="Path to the .frax file")
    f.set_defaults(func=_cmd_frax_info)

    v = sub.add_parser("validate-catalogue", help="Run the YAML catalogue validator.")
    v.set_defaults(func=_cmd_validate_catalogue)

    ver = sub.add_parser("version", help="Print engine version.")
    ver.set_defaults(func=_cmd_version)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
