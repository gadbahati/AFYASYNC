from __future__ import annotations

import ast
from pathlib import Path


MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _revision_graph() -> tuple[dict[str, set[str]], set[str]]:
    revisions: dict[str, set[str]] = {}
    parents: set[str] = set()

    for path in MIGRATIONS.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        revision = None
        down_revision: str | tuple[str, ...] | None = None
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "revision":
                    revision = ast.literal_eval(node.value)
                elif target.id == "down_revision":
                    down_revision = ast.literal_eval(node.value)

        if not isinstance(revision, str):
            continue
        if down_revision is None:
            parent_values: tuple[str, ...] = ()
        elif isinstance(down_revision, str):
            parent_values = (down_revision,)
        else:
            parent_values = tuple(down_revision)

        revisions[revision] = set(parent_values)
        parents.update(parent_values)

    return revisions, parents


def test_migration_graph_has_single_head() -> None:
    revisions, parents = _revision_graph()
    heads = set(revisions) - parents
    assert heads == {"0027_merge_migration_heads"}


def test_merge_revision_includes_all_previous_heads() -> None:
    revisions, _ = _revision_graph()
    merge_parents = revisions["0027_merge_migration_heads"]
    assert merge_parents == {
        "0026_post_hardening_permissions",
        "0016_patient_access_permissions",
        "0016_patient_record_permission",
        "0016_patient_record_write_permission",
        "0015_department_write_permission",
    }
