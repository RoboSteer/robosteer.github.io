"""Install the public adapter files into clean, fixed upstream checkouts."""
from pathlib import Path
import argparse
import shutil
import subprocess

LDA_COMMIT = "9b0885b699913b55283c24ad624bd4e8e8ed957c"
GMR_COMMIT = "bb1bbe40774794fceb2a7c579a3464a28e68c844"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--lda-root", type=Path, required=True)
    parser.add_argument("--gmr-root", type=Path, required=True)
    parser.add_argument("--apply-inference-patch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    package = args.package_root.expanduser().resolve()
    lda = args.lda_root.expanduser().resolve()
    gmr = args.gmr_root.expanduser().resolve()
    for name, root, revision in [("LDA", lda, LDA_COMMIT), ("GMR", gmr, GMR_COMMIT)]:
        if not (root / ".git").exists():
            parser.error(f"{name} is not a Git checkout: {root}")
        if git(root, "rev-parse", "HEAD") != revision:
            parser.error(f"{name} must be at {revision}; use a clean checkout")
        if git(root, "status", "--porcelain", "--untracked-files=normal"):
            parser.error(f"{name} checkout is dirty: {root}")
    files = []
    for source in sorted((package / "adapters/lda_utils").glob("*.py")):
        files.append((source, lda / "utils" / source.name))
    for source in sorted((package / "adapters/gmr").glob("*.py")):
        files.append((source, gmr / "scripts" / source.name))
    for source, destination in files:
        print(f"copy {source.relative_to(package)} -> {destination}")
        if not args.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    if args.apply_inference_patch:
        patch = package / "patches/lda/inference.patch"
        print(f"apply {patch.relative_to(package)} -> {lda}")
        if not args.dry_run:
            subprocess.run(["git", "-C", str(lda), "apply", str(patch)], check=True)


if __name__ == "__main__":
    main()
