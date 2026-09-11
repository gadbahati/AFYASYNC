import re
from pathlib import Path

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _load_revisions() -> dict[str, tuple[str, ...]]:
    """Parse revision/down_revision out of every migration file without importing Alembic."""
    revisions: dict[str, tuple[str, ...]] = {}
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        text = path.read_text()
        rev_match = re.search(r'^revision\s*=\s*["\']([^"\']+)["\']', text, re.M)
        if not rev_match:
            continue
        revision = rev_match.group(1)
        down_match = re.search(r'^down_revision\s*=\s*(.+?)$', text, re.M)
        if not down_match or down_match.group(1).strip() == "None":
            revisions[revision] = ()
            continue
        raw = down_match.group(1)
        if raw.strip().startswith("("):
            block_match = re.search(r"down_revision\s*=\s*\((.*?)\)", text, re.S)
            raw = block_match.group(1) if block_match else raw
        down_ids = tuple(re.findall(r'["\']([^"\']+)["\']', raw))
        revisions[revision] = down_ids
    return revisions


def test_migration_graph_has_a_single_head() -> None:
    """Guards against orphaned Alembic branches that `alembic upgrade head` cannot resolve.

    This does not require a database: it statically parses every migration
    file\'s revision/down_revision and checks the graph converges on exactly
    one head. A dangling branch here means a deployment will either fail
    outright ("Multiple head revisions are present") or, depending on how
    upgrade is invoked, silently skip an entire branch of schema/permission
    changes.
    """
    revisions = _load_revisions()
    assert revisions, "expected to find migration version files"

    referenced_as_parent: set[str] = set()
    for parents in revisions.values():
        referenced_as_parent.update(parents)

    heads = [rev for rev in revisions if rev not in referenced_as_parent]

    assert len(heads) == 1, (
        "Alembic migration graph must resolve to exactly one head; "
        f"found {len(heads)}: {sorted(heads)}. "
        "Add every unmerged head to a merge revision\'s down_revision tuple."
    )


def test_every_referenced_parent_revision_exists() -> None:
    revisions = _load_revisions()
    all_parents = {parent for parents in revisions.values() for parent in parents}
    missing = all_parents - set(revisions)
    assert not missing, f"down_revision references missing migration file(s): {sorted(missing)}"
