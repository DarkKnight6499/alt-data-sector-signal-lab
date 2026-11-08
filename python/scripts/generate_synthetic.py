"""Rebuild the deterministic demo snapshot and adapter fixtures."""

from altdata_lab.synthetic import write_snapshot

# Config: all generator parameters live in altdata_lab.config and synthetic.

if __name__ == "__main__":
    manifest = write_snapshot()
    print(f"Synthetic snapshot generated with seed {manifest['seed']}")
