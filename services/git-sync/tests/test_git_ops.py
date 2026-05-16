from unittest.mock import patch, MagicMock, call
from git_ops import sync_vault


def _run(returncode=0, stderr=""):
    m = MagicMock()
    m.returncode = returncode
    m.stderr = stderr
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
    calls = mock_run.call_args_list
    assert calls[0][0][0] == ["git", "-C", "/vault", "add", "-A"]
    assert calls[1][0][0] == ["git", "-C", "/vault", "diff", "--cached", "--quiet"]
    assert calls[2][0][0][:5] == ["git", "-C", "/vault", "commit", "-m"]
    assert calls[3][0][0] == ["git", "-C", "/vault", "push"]


@patch("git_ops.subprocess.run")
def test_skips_commit_when_nothing_to_commit(mock_run):
    mock_run.side_effect = [
        _run(),    # git add -A
        _run(0),   # diff --cached --quiet → 0 = нет изменений
    ]
    sync_vault("/vault", "Bot", "bot@example.com")
    assert mock_run.call_count == 2


@patch("git_ops.subprocess.run")
def test_raises_descriptive_error_on_git_failure(mock_run):
    mock_run.side_effect = [
        _run(128, stderr="not a git repository"),  # git add -A fails
    ]
    try:
        sync_vault("/vault", "Bot", "bot@example.com")
        assert False, "should have raised"
    except RuntimeError as e:
        assert "not a git repository" in str(e)
