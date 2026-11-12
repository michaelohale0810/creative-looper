import pytest

from creative_looper.main import parse_args


def fails(argv, capsys, message):
    with pytest.raises(SystemExit):
        parse_args(argv)
    assert message in capsys.readouterr().err


def test_loop_options_parse_with_defaults():
    args = parse_args(["--loop"])
    assert args.loop and args.max_runs is None
    assert str(args.primary_file) == "domains/primary_domains.txt"
    args = parse_args(["--loop", "--max-runs", "3", "--primary-file", "p.txt", "--target-file", "t.txt"])
    assert args.max_runs == 3 and str(args.target_file) == "t.txt"


def test_loop_rejects_conflicting_options(capsys):
    fails(["--loop", "Geology", "Jazz"], capsys, "drop the domains")
    fails(["--max-runs", "3"], capsys, "only applies with --loop")
    fails(["--loop", "--max-runs", "0"], capsys, "at least 1")


def test_single_run_arguments_still_work():
    args = parse_args(["Geology", "Jazz"])
    assert (args.primary, args.target, args.loop) == ("Geology", "Jazz", False)
