from unittest.mock import patch, MagicMock
from git_ops import sync_vault


def _run(returncode=0):
    m = MagicMock()
    m.returncode = returncode
    return m


@patch("git_ops.subprocess.run")
def test_commits_and_pushes_when_changes_exist(mock_run):
    mock_run.side_effect = [
        _run(),    # git add -A
        _run(1),   # diff --cached --quiet → 1 = есть изменения
        _run(),    # git commit
        _run(),    # git push
    ]
    sync_vault("/vault", "Bot", "bot@example.com")
    assert mock_run.call_count == 4


@patch("git_ops.subprocess.run")
def test_skips_commit_when_nothing_to_commit(mock_run):
    mock_run.side_effect = [
        _run(),    # git add -A
        _run(0),   # diff --cached --quiet → 0 = нет изменений
    ]
    sync_vault("/vault", "Bot", "bot@example.com")
    assert mock_run.call_count == 2
