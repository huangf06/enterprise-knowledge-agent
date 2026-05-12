#!/usr/bin/env python3
"""Generate cross-source synthetic data. Thin CLI over src.data.generator.generate_all."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data.generator import generate_all


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic"),
        help="Output directory (one subdirectory per source).",
    )
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    stats = generate_all(seed=args.seed, output_dir=args.output, days=args.days)
    print(f"Generated cross-source synthetic data at {args.output} (seed={args.seed}, days={args.days})")
    print(json.dumps(stats, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
