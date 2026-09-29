"""review.py: the review page, its API, the redo list and the gate."""
import json
import os
from fractions import Fraction
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest

import review
from conftest import (SCRIPTS, SFX_FILES, graphics_body, graphics_world, run_script,
                      write_graphics_spec)
from validate import validate_file

pytestmark = pytest.mark.skipif(not (shutil.which("node") and shutil.which("ffmpeg")),
                                reason="needs node and ffmpeg")


def render(world, *extra):
    env = {**os.environ, "CLAUDE_CUT_FAKE_RENDER": "1"}
    return subprocess.run([sys.executable, str(SCRIPTS / "render_graphics.py"),
                           str(world["gfx"]), "--shoot", str(world["shoot"]), *extra],
                          capture_output=True, text=True, env=env)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    w = graphics_world(tmp_path_factory.mktemp("review"))
    write_graphics_spec(w, graphics_body(w))
    r = render(w)
    assert r.returncode == 0, r.stderr
    return w


@pytest.fixture(scope="module")
def server(world):
    srv = review.make_server(world["gfx"], 0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def post(base, body):
    req = urllib.request.Request(base + "/api/review", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def manifest(world):
    return json.loads((world["gfx"] / "renders" / "manifest.json").read_text())


def test_page_lists_every_render_and_effect_in_timeline_order(world, server):
    code, _, body = get(server + "/")
    page = body.decode()
    assert code == 200 and "<title>Graphics review</title>" in page
    m = manifest(world)
    cues = {c["id"]: c for c in world["plan"]["cues"]}
    everything = [r["cue"] for r in m["renders"]] + [s["cue"] for s in m["sfx"]["items"]]
    order = sorted(everything, key=lambda c: (cues[c]["tl"][0], cues[c]["kind"] == "sfx", c))
    positions = [page.index(f'data-cue="{c}"') for c in order]
    assert positions == sorted(positions)          # graphics and effects interleaved
    first = cues[order[0]]["tl"][0]
    assert f"<span>{review.tc(first, Fraction(25))}</span>" in page
    assert review.tc(3 * 3600 * 25 + 25 * 61 + 7, Fraction(25)) == "03:01:01:07"
    for r in m["renders"]:
        assert f'src="/files/{r["proxy"]}?v={r["sha256"][:12]}#t=0.5"' in page
    sfx = m["sfx"]["items"][0]
    assert f'data-cue="{sfx["cue"]}" data-kind="sfx"' in page
    assert "Whoosh - Pan - Heavy" in page and "(current)" in page     # alternative offered
    assert 'class="said"' in page                                       # spoken words shown


def test_proxies_stream_with_ranges_and_nothing_escapes(world, server):
    proxy = manifest(world)["renders"][0]["proxy"]
    code, headers, body = get(f"{server}/files/{proxy}", {"Range": "bytes=0-99"})
    assert code == 206 and len(body) == 100
    assert headers["Content-Range"].startswith("bytes 0-99/")
    assert headers["Content-Type"] == "video/mp4"
    assert get(f"{server}/files/../plan.resolved.json")[0] == 404
    assert get(f"{server}/files/%2e%2e/plan.resolved.json")[0] == 404


def test_sfx_players_serve_only_listed_library_files(world, server):
    from urllib.parse import quote
    code, headers, _ = get(f"{server}/sfx/story/{quote(SFX_FILES[1][0])}")
    assert code == 200 and headers["Content-Type"].startswith("audio/")
    assert get(f"{server}/sfx/story/{quote(SFX_FILES[2][0])}")[0] == 404  # not offered
    assert get(f"{server}/sfx/story/../../plan.resolved.json")[0] == 404


def test_decisions_are_written_to_the_manifest(world, server):
    m = manifest(world)
    a, b = m["renders"][0]["cue"], m["renders"][1]["cue"]
    assert post(server, {"cue": a, "kind": "graphic", "status": "approved"}) == \
        (200, {"status": "approved", "note": ""})
    code, rv = post(server, {"cue": b, "kind": "graphic", "status": "redo",
                             "note": "  kicker should say Key term  "})
    assert code == 200 and rv["note"] == "kicker should say Key term"
    by = {r["cue"]: r["review"] for r in manifest(world)["renders"]}
    assert by[a]["status"] == "approved" and by[b]["status"] == "redo"
    assert validate_file(world["gfx"] / "renders" / "manifest.json") == ("graphics", [])


def test_choosing_another_sound_is_a_swap_request(world, server):
    cue = manifest(world)["sfx"]["items"][0]["cue"]
    code, rv = post(server, {"cue": cue, "kind": "sfx", "status": "approved",
                             "swap": SFX_FILES[1][0]})
    assert code == 200 and rv == {"status": "redo", "note": "", "swap": SFX_FILES[1][0]}
    # choosing the current file again is a plain decision
    code, rv = post(server, {"cue": cue, "kind": "sfx", "status": "approved",
                             "swap": SFX_FILES[0][0]})
    assert rv == {"status": "approved", "note": ""}


def test_bad_requests_are_refused(world, server):
    g = manifest(world)["renders"][0]["cue"]
    assert post(server, {"cue": "b99.mg1", "kind": "graphic", "status": "approved"})[0] == 400
    assert post(server, {"cue": g, "kind": "graphic", "status": "maybe"})[0] == 400
    code, msg = post(server, {"cue": g, "kind": "graphic", "status": "redo",
                              "swap": "x.wav"})
    assert code == 400 and "only sound effects can be swapped" in msg


def test_todo_and_the_status_gate(world):
    gfx = world["gfx"]
    first = manifest(world)["renders"][2]["cue"]
    review.set_review(gfx, first, "graphic", "redo", "slower wipe")
    todo = json.loads(run_script("review.py", "todo", gfx).stdout)
    assert {"cue": first, "kind": "graphic", "note": "slower wipe"} in todo
    r = run_script("review.py", "status", gfx)
    assert r.returncode == 1 and "to redo" in r.stdout
    for kind, e in review.items(manifest(world)):
        review.set_review(gfx, e["cue"], kind, "approved")
    r = run_script("review.py", "status", gfx)
    assert r.returncode == 0 and r.stdout.startswith(f"{r.stdout.split()[0]} approved, 0 to redo, 0 pending")


def test_the_redo_loop_rerenders_only_what_was_sent_back(world):
    gfx = world["gfx"]
    m = manifest(world)
    for kind, e in review.items(m):
        review.set_review(gfx, e["cue"], kind, "approved")
    body = graphics_body(world)
    lt = next(g for g in body["graphics"] if g["template"] == "lowerThird")
    review.set_review(gfx, lt["cue"], "graphic", "redo", "say 'Key term' instead")
    # the skill applies the note, then re-renders just that cue
    lt["vars"]["kicker"] = "Key term!"
    write_graphics_spec(world, body)
    r = render(world, "--only", lt["cue"])
    assert r.returncode == 0, r.stderr
    after = {e["cue"]: e["review"]["status"] for _, e in review.items(manifest(world))}
    assert after.pop(lt["cue"]) == "pending"
    assert set(after.values()) == {"approved"}
