from miner.detector import is_gh_aw_workflow


def test_gh_aw_with_matching_pair():
    files = ["report.md", "report.lock.yml", "ci.yml"]
    assert is_gh_aw_workflow(files) is True


def test_gh_aw_only_markdown():
    files = ["report.md", "ci.yml"]
    assert is_gh_aw_workflow(files) is False


def test_gh_aw_only_lock():
    files = ["report.lock.yml", "ci.yml"]
    assert is_gh_aw_workflow(files) is False


def test_gh_aw_mismatched_names():
    files = ["report.md", "other.lock.yml"]
    assert is_gh_aw_workflow(files) is False


def test_gh_aw_multiple_files_one_pair():
    files = ["build.yml", "deploy.md", "daily-task.md", "daily-task.lock.yml"]
    assert is_gh_aw_workflow(files) is True