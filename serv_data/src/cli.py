"""Command line interface for SettleSaathi data generator, validator, and repeatability suite."""

import argparse
import sys
import tempfile
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from serv_data.src.generator import SyntheticDataGenerator
from serv_data.src.invalid_fixtures import generate_invalid_fixtures
from serv_data.src.validator import FixtureValidator
from serv_data.src.constants import DATASET_VERSION, DEFAULT_RANDOM_SEED, FIXED_AS_OF_TIMESTAMP


def cmd_generate(args):
    """Generate synthetic fixtures and manifest."""
    output_dir = Path(args.output)
    mirror_dir = Path(args.mirror) if args.mirror else None

    print(f"Generating synthetic fixtures in: {output_dir}")
    generator = SyntheticDataGenerator(
        output_dir=output_dir,
        dataset_version=args.version,
        seed=args.seed,
        as_of_timestamp=args.as_of,
    )
    manifest = generator.generate(mirror_to_root=mirror_dir)

    print(f"Generating invalid test fixtures in: {output_dir / 'invalid'}")
    generate_invalid_fixtures(output_dir, mirror_to_root=mirror_dir)

    print(f"Successfully generated {len(manifest['files'])} core files across {len(manifest['scenarios'])} scenarios.")
    print("Record counts:")
    for k, v in manifest["record_counts"].items():
        print(f"  - {k}: {v}")

    # Generate validation report
    validator = FixtureValidator(output_dir)
    report_md = validator.generate_report_markdown()
    report_path = output_dir / "validation_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    if mirror_dir:
        (mirror_dir / "validation_report.md").write_text(report_md, encoding="utf-8")
    print(f"Validation report written to: {report_path}")


def cmd_validate(args):
    """Validate fixtures against financial and safety rules."""
    fixture_dir = Path(args.fixture_dir)
    print(f"Validating fixtures in: {fixture_dir}")
    validator = FixtureValidator(fixture_dir)
    passed, summary = validator.validate_all()

    print(f"Checks passed: {summary['checks_passed']}")
    if passed:
        print("SUCCESS: All financial integrity, balance, and synthetic safety checks passed.")
        sys.exit(0)
    else:
        print(f"FAILED: Found {len(summary['errors'])} errors:")
        for err in summary["errors"]:
            print(f"  - {err}")
        sys.exit(1)


def cmd_test_determinism(args):
    """Prove repeatability by generating twice and comparing artifact checksums."""
    print("Testing generator determinism across two isolated runs...")
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        dir1 = Path(tmp1)
        dir2 = Path(tmp2)

        gen1 = SyntheticDataGenerator(dir1, seed=args.seed, as_of_timestamp=args.as_of)
        m1 = gen1.generate()

        gen2 = SyntheticDataGenerator(dir2, seed=args.seed, as_of_timestamp=args.as_of)
        m2 = gen2.generate()

        mismatch = False
        for fname, meta1 in m1["files"].items():
            meta2 = m2["files"].get(fname)
            if not meta2:
                print(f"FAILED: File {fname} missing from run 2")
                mismatch = True
                continue
            if meta1["sha256"] != meta2["sha256"]:
                print(f"FAILED: Hash mismatch on {fname}:")
                print(f"  Run 1: {meta1['sha256']}")
                print(f"  Run 2: {meta2['sha256']}")
                mismatch = True
            else:
                print(f"MATCH: {fname} -> {meta1['sha256'][:16]}...")

        if mismatch:
            print("Determinism test FAILED.")
            sys.exit(1)
        else:
            print("SUCCESS: Generator is 100% deterministic! Identical SHA-256 hashes produced.")


def main():
    parser = argparse.ArgumentParser(description="SettleSaathi Data Generator & Validator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic fixtures")
    gen_parser.add_argument("--output", default="serv_data/fixtures/v1", help="Output directory")
    gen_parser.add_argument("--mirror", default="fixtures/synthetic/v1", help="Optional root mirror directory")
    gen_parser.add_argument("--version", default=DATASET_VERSION, help="Dataset version")
    gen_parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED, help="Random seed")
    gen_parser.add_argument("--as-of", default=FIXED_AS_OF_TIMESTAMP, help="Fixed as-of timestamp")
    gen_parser.set_defaults(func=cmd_generate)

    # validate command
    val_parser = subparsers.add_parser("validate", help="Validate fixture files")
    val_parser.add_argument("--fixture-dir", default="serv_data/fixtures/v1", help="Directory of fixtures to check")
    val_parser.set_defaults(func=cmd_validate)

    # test-determinism command
    det_parser = subparsers.add_parser("test-determinism", help="Verify repeatability of generator")
    det_parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED, help="Random seed")
    det_parser.add_argument("--as-of", default=FIXED_AS_OF_TIMESTAMP, help="Fixed as-of timestamp")
    det_parser.set_defaults(func=cmd_test_determinism)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
