#!/usr/bin/env python3
"""Seed initial identities into the data store."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from identity.generator import IdentityGenerator
from identity.persistence import IdentityStore
from identity.scoring import IdentityScorer
from fingerprint.manager import FingerprintManager
from fingerprint.consistency import FingerprintConsistencyValidator


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed identities")
    parser.add_argument("-n", "--count", type=int, default=10, help="Number of identities to create")
    parser.add_argument("--locale", default=None, help="Force a specific locale")
    parser.add_argument("--os", dest="os_name", default=None, help="Force a specific OS")
    parser.add_argument("--output-dir", default="data/identities", help="Output directory")
    args = parser.parse_args()

    generator = IdentityGenerator()
    validator = FingerprintConsistencyValidator()
    fp_manager = FingerprintManager(generator, validator)
    store = IdentityStore(args.output_dir)
    scorer = IdentityScorer()

    print(f"Generating {args.count} identities...\n")

    for i in range(args.count):
        kwargs = {}
        if args.locale:
            kwargs["locale"] = args.locale
        if args.os_name:
            kwargs["os_name"] = args.os_name

        identity = fp_manager.generate_consistent_identity(**kwargs)
        score = scorer.score(identity)
        identity.reputation_score = score

        store.save(identity)
        print(f"  [{i+1:3d}] {identity.alias:16s} | {identity.persona_name:24s} | "
              f"{identity.device.os_name:8s}/{identity.device.browser_name:8s} | "
              f"{identity.device.locale:5s} | score={score:.2f}")

    print(f"\n✓ {args.count} identities saved to {args.output_dir}/")
    print(f"  Unique fingerprints: {fp_manager.known_fingerprints}")


if __name__ == "__main__":
    main()
