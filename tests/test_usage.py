"""Run time and tokens read: counted only inside a run, summed per run, day and week."""
from dsys import usage


def test_counts_only_inside_a_run_and_summarises(repo):
    root = repo.root
    usage.add(root, "candidates news", 4000)  # no run in progress: not counted
    usage.start(root, "daily", "2026-11-26")
    usage.add(root, "candidates news --category science", 8000)
    usage.add(root, "candidates news --category world", 4000)
    usage.add(root, "papers stage2", 40000)
    row = usage.end(root)
    assert row["run"] == "daily" and row["minutes"] == 0
    assert row["read_chars"] >= 52000 and row["est_tokens_read"] == row["read_chars"] // 4
    assert row["biggest"][0] == ("papers, final choice", 40000)
    assert ("news", 12000) in row["biggest"]
    t = usage.table(usage.summary(root, usage.week_days("2026-W48")))
    assert "| 2026-11-26 | daily | 0 |" in t and "**total**" in t


def test_prompt_chars_follow_the_runbook():
    from conftest import ROOT
    assert usage.prompt_chars(ROOT, "weekly") > usage.prompt_chars(ROOT, "quarterly") > 0
