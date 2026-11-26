"""Output a run can read in full: nothing silently cut by tool limits."""
import io

from dsys import readable


def test_short_output_is_printed_as_is(tmp_path):
    out = io.StringIO()
    readable.emit('{"a": 1}\n', "x", out=out, workdir=tmp_path)
    assert out.getvalue() == '{"a": 1}\n' and not (tmp_path / "out").exists()


def test_long_output_goes_to_parts_that_keep_everything(tmp_path):
    obj = {"kind": "videos", "candidates": [{"id": i, "d": "word " * 400} for i in range(300)]}
    out = io.StringIO()
    readable.emit("x" * (readable.LIMIT + 1), "candidates videos", out=out, workdir=tmp_path, obj=obj)
    msg = out.getvalue().splitlines()
    paths = [line for line in msg if line.startswith(str(tmp_path))]
    assert "Read every part" in msg[0] and len(paths) > 1
    text = "".join(open(p).read() for p in paths)
    for p in paths:
        body = open(p).read()
        assert len(body) <= readable.PART + readable.WIDTH
        assert max(len(line) for line in body.splitlines()) <= readable.WIDTH
    # every record is there, and unwrapping restores each line
    joined = text.replace("\n" + readable.CONT, "")
    assert joined.count('{"id":') == 300 and "candidates: (300, one per line)" in text


def test_rerun_replaces_old_parts(tmp_path):
    stem = tmp_path / "out" / "s"
    readable.write_parts("a\n" * 50000, stem, size=10000)
    n = len(list(stem.parent.glob("s-*.txt")))
    readable.write_parts("short\n", stem, size=10000)
    assert n > 1 and len(list(stem.parent.glob("s-*.txt"))) == 1
