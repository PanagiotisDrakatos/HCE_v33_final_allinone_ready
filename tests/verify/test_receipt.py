"""tree_hash and inputs_digest behaviour, exercised against a throwaway git
repo. A rebase-identical tree keeps its hash; any working-tree change (edit,
new untracked file, deletion) invalidates it; changing a declared input file
changes the inputs digest."""

import subprocess

import verify_core as core


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _repo(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "a.txt").write_text("one\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def test_clean_tree_hash_matches_git(tmp_path):
    root = _repo(tmp_path)
    tree, dirty, diff = core.git_tree_hash(str(root))
    expect = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], capture_output=True, text=True
    ).stdout.strip()
    assert tree == expect and dirty is False and diff == ""


def test_amend_identical_content_keeps_tree(tmp_path):
    root = _repo(tmp_path)
    t1, _, _ = core.git_tree_hash(str(root))
    _git(root, "commit", "-q", "--amend", "-m", "reworded")  # new commit, same tree
    t2, _, _ = core.git_tree_hash(str(root))
    assert t1 == t2


def test_edit_invalidates_tree(tmp_path):
    root = _repo(tmp_path)
    clean, _, _ = core.git_tree_hash(str(root))
    (root / "a.txt").write_text("two\n")
    dirty_tree, dirty, diff = core.git_tree_hash(str(root))
    assert dirty is True and dirty_tree != clean and diff != ""


def test_untracked_file_invalidates_tree(tmp_path):
    root = _repo(tmp_path)
    clean, _, _ = core.git_tree_hash(str(root))
    (root / "new.txt").write_text("x\n")
    dirty_tree, dirty, _ = core.git_tree_hash(str(root))
    assert dirty is True and dirty_tree != clean


def test_deletion_invalidates_tree(tmp_path):
    root = _repo(tmp_path)
    clean, _, _ = core.git_tree_hash(str(root))
    (root / "a.txt").unlink()
    dirty_tree, dirty, _ = core.git_tree_hash(str(root))
    assert dirty is True and dirty_tree != clean


def test_inputs_digest_changes_with_a_declared_file(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "docker-compose.yml").write_text("a")
    d1 = core.inputs_digest(str(root), files=("docker-compose.yml",))
    (root / "docker-compose.yml").write_text("b")
    d2 = core.inputs_digest(str(root), files=("docker-compose.yml",))
    assert d1 != d2


def test_inputs_digest_records_missing_file(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    present = core.inputs_digest(str(root), files=("x",))
    (root / "x").write_text("")
    now_present = core.inputs_digest(str(root), files=("x",))
    assert present != now_present  # absent -> sentinel differs from empty file
