"""pipeline.py: produce's state engine on the synthetic MCP chain. Stages
complete in order behind their gates, staleness comes from the files on
disk, --from sends later stages stale, --to stops, and the graphics gate
needs the review finished."""
import json
import shutil

import pytest

import pipeline as pl
from conftest import FIXTURES, run_script, synthetic_cut
from validate import validate_file

MCP = FIXTURES / "mcp-setup"


def pipe(w, *args):
    return run_script("pipeline.py", "--dir", w, *args)


def nxt(w, *args):
    r = pipe(w, "next", "--json", *args)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def status(w):
    return {r["stage"]: r for r in json.loads(pipe(w, "status", "--json").stdout)}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    d = tmp_path_factory.mktemp("pipe")
    vault = d / "vault"
    shutil.copytree(MCP, vault)
    shutil.copyfile(vault / "legacy" / "claude-code-wordpress-mcp-setup-script-v2.md",
                    vault / "mcp-setup.md")
    w = d / "footage"
    w.mkdir()
    return {"d": d, "vault": vault, "w": w, "script": vault / "mcp-setup.md"}


def test_init_starts_everything_pending(world):
    r = pipe(world["w"], "init", "--script", world["script"])
    assert r.returncode == 0, r.stderr
    assert validate_file(world["w"] / "pipeline.json") == ("pipeline", [])
    s = status(world["w"])
    assert all(r["status"] == "pending" for r in s.values())
    assert nxt(world["w"]) ["stage"] == "paper-edit"
    paths = json.loads(pipe(world["w"], "paths").stdout)
    assert paths["paper_edit"] == str(world["vault"] / "mcp-setup.paper-edit.json")
    assert paths["th_fcpxml"] == str(world["w"] / "mcp-setup_cut.fcpxml")
    other = world["vault"] / "other.md"
    other.write_text("x")
    r = pipe(world["w"], "init", "--script", other)
    assert r.returncode == 1 and "one video" in r.stderr


def test_a_stage_cant_start_before_the_one_before_it(world):
    r = pipe(world["w"], "start", "conform")
    assert r.returncode == 1 and "paper-edit, director, shoot, cut are not complete" in r.stderr


def test_paper_edit_and_director_stop_at_their_gates(world):
    w = world["w"]
    for stage in ("paper-edit", "director"):
        assert pipe(w, "start", stage).returncode == 0
        assert pipe(w, "done", stage).returncode == 0
        n = nxt(w)
        assert (n["action"], n["stage"]) == ("gate", stage)
        assert ".md" in n["message"]
        assert pipe(w, "approve", stage).returncode == 0
    assert nxt(w) == {**nxt(w), "action": "run", "stage": "shoot", "step": "pack"}


def test_shoot_waits_for_the_recording_then_registers(world):
    w, vault = world["w"], world["vault"]
    director = vault / "mcp-setup.director.json"
    pipe(w, "start", "shoot")
    assert run_script("shoot.py", "pack", "--director", director,
                      "-o", w / "shoot-pack.md").returncode == 0
    r = pipe(w, "done", "shoot")
    assert r.returncode == 1 and "shoot.json" in r.stderr          # not registered yet
    assert pipe(w, "wait", "shoot", "--reason", "recording").returncode == 0
    n = nxt(w)
    assert (n["action"], n["stage"]) == ("wait", "shoot")

    # the director changes while recording: the pack is out of date, and the
    # approved director needs approving again
    keep = director.read_text()
    director.write_text(keep + "\n")
    s = status(w)
    assert s["shoot"]["status"] == "stale"
    assert s["director"]["gate"] == "waiting"
    assert "changed since you approved it" in s["director"]["reasons"][0]
    director.write_text(keep)
    assert nxt(w)["action"] == "wait"

    for f in ("aroll.mp4", "vo.wav"):
        (w / f).write_bytes(b"x")
    assert run_script("shoot.py", "scan", w, "--director", director).returncode == 0
    assert run_script("shoot.py", "write", w / "shoot.draft.json",
                      "--director", director).returncode == 0
    pipe(w, "start", "shoot")
    assert nxt(w)["step"] == "register"
    assert pipe(w, "done", "shoot").returncode == 0
    assert pipe(w, "approve", "shoot").returncode == 0
    assert nxt(w)["stage"] == "cut"


def test_cut_needs_both_recordings_cut(world):
    w = world["w"]
    pipe(w, "start", "cut")
    r = pipe(w, "done", "cut")
    assert r.returncode == 1
    for name in ("th/cuts.json", "th/sentences.json", "mcp-setup_cut.fcpxml",
                 "vo/cuts.json", "vo/sentences.json"):
        assert name in r.stderr
    synthetic_cut(world["vault"], w / ".claude-cut")
    shutil.copyfile(w / ".claude-cut" / "th" / "cut.fcpxml", w / "mcp-setup_cut.fcpxml")
    assert pipe(w, "done", "cut").returncode == 0, pipe(w, "done", "cut").stderr
    assert nxt(w, "--to", "cut")["action"] == "gate"
    assert pipe(w, "approve", "cut").returncode == 0
    n = nxt(w, "--to", "cut")
    assert (n["action"], n["stage"]) == ("stop", "cut")


def test_conform_has_no_gate(world):
    w, v = world["w"], world["vault"]
    pipe(w, "start", "conform")
    r = run_script("conform.py", "--director", v / "mcp-setup.director.json",
                   "--map", v / "prompter.map.json", "--th", w / ".claude-cut" / "th",
                   "--th-fcpxml", w / "mcp-setup_cut.fcpxml",
                   "--vo", w / ".claude-cut" / "vo", "-o", w / "plan.resolved.json")
    assert r.returncode == 0, r.stdout
    assert pipe(w, "done", "conform").returncode == 0
    s = status(w)
    assert s["conform"]["complete"] and s["conform"]["gate"] == "n/a"
    assert nxt(w)["stage"] == "graphics"


def test_a_changed_input_makes_the_stage_stale(world):
    w = world["w"]
    cuts = w / ".claude-cut" / "th" / "cuts.json"
    keep = cuts.read_text()
    cuts.write_text(keep + " ")
    s = status(w)
    assert s["conform"]["status"] == "stale"
    assert "cuts.json has changed" in s["conform"]["reasons"]
    assert s["cut"]["gate"] == "waiting"                  # changed since approved
    n = nxt(w)
    assert (n["action"], n["stage"]) == ("gate", "cut")
    cuts.write_text(keep)
    assert status(w)["conform"]["complete"]


def test_the_graphics_gate_needs_the_review_finished(world, tmp_path):
    w = world["w"]
    state = pl.read(w)
    p = pl.layout(state)
    man = p["graphics_manifest"]
    man.parent.mkdir(parents=True, exist_ok=True)
    doc = {"renders": [{"cue": "b01.mg1", "review": {"status": "pending", "note": ""}}],
           "sfx": {"items": [{"cue": "b01.sfx1", "review": {"status": "approved"}}]}}
    man.write_text(json.dumps(doc))
    p["graphics_spec"].write_text("{}")
    state["stages"]["graphics"].update({"status": "done", "gate": "waiting",
                                        "inputs": pl.prints([p["plan"]]),
                                        "outputs": pl.prints([man, p["graphics_spec"]])})
    pl.save(w, state)
    n = nxt(w)
    assert (n["action"], n["stage"]) == ("gate", "graphics")
    assert "(1 approved, 0 sent back, 1 pending)" in n["message"]
    r = pipe(w, "approve", "graphics")
    assert r.returncode == 1 and "the review isn't finished" in r.stderr
    doc["renders"][0]["review"]["status"] = "approved"
    man.write_text(json.dumps(doc))
    assert pipe(w, "approve", "graphics").returncode == 0
    assert nxt(w)["stage"] == "assemble"


def test_reset_from_sends_later_stages_stale(world):
    w = world["w"]
    before = pl.read(w)
    r = pipe(w, "reset", "--from", "director")
    assert r.returncode == 0
    assert "reset: director, shoot, cut, conform, graphics" in r.stdout
    s = status(w)
    assert s["paper-edit"]["complete"]
    assert s["director"]["status"] == "pending"
    for stage in ("shoot", "cut", "conform", "graphics"):
        assert s[stage]["status"] == "stale", stage
        assert s[stage]["reasons"] == ["director is being redone"]
    assert s["assemble"]["status"] == "pending"
    assert nxt(w)["stage"] == "director"
    pl.save(w, before)


def test_status_text_is_readable(world):
    out = pipe(world["w"], "status").stdout
    assert "mcp-setup.md ->" in out
    assert "✓ paper-edit" in out and "next: run assemble" in out
