import json

import pytest

from conftest import MCP_LEGACY, run_script
from validate import validate_file


def errors(path):
    kind, errs = validate_file(path)
    return errs


# --- happy path ------------------------------------------------------------

def test_valid_chain(chain):
    chain.build()
    for f in (chain.script_json, chain.paper_edit, chain.director):
        assert errors(f) == [], f.name
    r = run_script("validate.py", chain.script_json, chain.paper_edit,
                   chain.director)
    assert r.returncode == 0, r.stdout
    assert r.stdout.count("OK") == 3


# --- legacy and non-handoff files --------------------------------------------

def test_legacy_paper_edit_rejected():
    r = run_script("validate.py",
                   MCP_LEGACY / "claude-code-wordpress-mcp-setup-paper-edit.md")
    assert r.returncode == 1
    assert "legacy paper edit (no segment IDs)" in r.stdout
    assert "re-run /claude-cut:paper-edit" in r.stdout


def test_legacy_director_rejected():
    r = run_script("validate.py", MCP_LEGACY /
                   "claude-code-wordpress-mcp-setup-script-v2-director.md")
    assert r.returncode == 1
    assert "legacy director file (no segment IDs)" in r.stdout
    assert "re-run /claude-cut:director on the new paper edit" in r.stdout


def test_rendered_markdown_points_at_json(chain, tmp_path):
    chain.build()
    md = tmp_path / "mini.paper-edit.md"
    assert run_script("render_md.py", chain.paper_edit, "-o", md).returncode == 0
    errs = errors(md)
    assert len(errs) == 1 and "rendered markdown view" in errs[0]


def test_json_without_schema(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    assert "not a claude-cut handoff file" in errors(p)[0]


# --- staleness ---------------------------------------------------------------

def test_stale_script_is_reported(chain):
    chain.build()
    doc = json.loads(chain.script_json.read_text())
    doc["title"] = "changed"
    chain.script_json.write_text(json.dumps(doc))
    errs = errors(chain.paper_edit)
    assert len(errs) == 1 and "stale" in errs[0]
    assert "stale" in errors(chain.director)[0]


# --- paper-edit rules ----------------------------------------------------------

def pe_errors(chain, mutate):
    chain.write_script().write_paper_edit(mutate)
    return errors(chain.paper_edit)


def test_gap_in_sentences(chain):
    def m(pe):
        pe["beats"][1]["sentences"] = [5, 5]  # skips sentence 4
        pe["beats"][2]["sentences"] = [6, 8]
        pe["beats"][2]["cues"] = []
    errs = pe_errors(chain, m)
    assert any("sentences 4-4 are not in any beat" in e for e in errs)


def test_overlap_and_tail(chain):
    def m(pe):
        pe["beats"][1]["sentences"] = [3, 4]
        pe["beats"][3]["sentences"] = [9, 9]
        pe["beats"].pop()  # drop b04 so 9 is uncovered
    errs = pe_errors(chain, m)
    assert any("b02: starts at sentence 3, overlapping" in e for e in errs)
    assert any("sentences 9-9 are not in any beat" in e for e in errs)


def test_beat_crossing_sections(chain):
    def m(pe):
        pe["beats"][1]["sentences"] = [4, 5]
        pe["beats"][2]["sentences"] = [6, 8]
        pe["beats"][2]["cues"] = [c for c in pe["beats"][2]["cues"]
                                  if c["id"] != "b03.sr1"]
    errs = pe_errors(chain, m)
    assert any("b02: section is sec01 but its sentences are in sec01, sec02"
               in e for e in errs)


def test_beat_ids_sequential(chain):
    def m(pe):
        pe["beats"][1]["id"] = "b05"
    errs = pe_errors(chain, m)
    assert any("b05: beat IDs must run b01, b02" in e for e in errs)


def test_cue_rules_all_listed(chain):
    def m(pe):
        cues = pe["beats"][2]["cues"]
        cues[1]["id"] = "b02.sr1"                    # wrong beat prefix
        cues[2]["anchor"]["phrase"] = "import button"  # not in sentence 6
        cues.append({"id": "b03.lt2", "kind": "lt", "placement": "bed",
                     "layer": "full", "brief": "bad bed"})
        cues.append({"id": "b03.mg1", "kind": "mg", "placement": "insert_after",
                     "layer": "full", "brief": "no duration"})
        cues.append({"id": "b03.callout1", "kind": "callout",
                     "placement": "overlay", "anchor": {"sentence": 2},
                     "brief": "anchor outside beat, no layer"})
        cues.append({"id": "b03.zoom1", "kind": "mg", "placement": "overlay",
                     "layer": "overlay", "brief": "kind mismatch"})
    errs = pe_errors(chain, m)
    expected = [
        "b02.sr1: cue is under beat b03 but its ID names b02",
        'b03.lt1: phrase "import button" is not in sentence 6',
        "b03.lt2: a bed must be sr, br or mg",
        "b03.mg1: insert_after needs duration",
        "b03.callout1: callout cues need a layer",
        "b03.callout1: anchor sentence 2 is outside beat b03",
        "b03.zoom1: ID says 'zoom' but kind is 'mg'",
    ]
    for want in expected:
        assert any(want in e for e in errs), (want, errs)


def test_cue_anchor_loop_and_unknown(chain):
    def m(pe):
        cues = pe["beats"][0]["cues"]
        cues[0]["anchor"] = {"cue": "b01.sfx1"}      # mg1 <-> sfx1 loop
        cues[2]["anchor"] = {"cue": "b01.mg9"}
    errs = pe_errors(chain, m)
    assert any("b01.mg1: cue anchors form a loop" in e for e in errs)
    assert any("b01.lt1: anchored to unknown cue b01.mg9" in e for e in errs)


def test_schema_error_bad_cue_id(chain):
    def m(pe):
        pe["beats"][0]["cues"][0]["id"] = "b01-mg1"
    errs = pe_errors(chain, m)
    assert any("does not match" in e for e in errs)


# --- director rules -------------------------------------------------------------

def d_errors(chain, mutate, pe_mutate=None):
    chain.build(pe_mutate, mutate)
    return errors(chain.director)


def test_director_missing_beat_and_unknown_beat(chain):
    def m(d):
        d["segments"].pop(1)  # drop b02
        d["segments"].append({"id": "b09", "beat": "b09", "mode": "th"})
    errs = d_errors(chain, m)
    assert any("b02: beat has no segment" in e for e in errs)
    assert any("b09: no beat b09 in the paper edit" in e for e in errs)


def test_director_split_shapes(chain):
    def m(d):
        d["segments"] = [
            {"id": "b01", "beat": "b01", "mode": "th"},
            {"id": "b01a", "beat": "b01", "sentences": [1, 3], "mode": "th"},
            {"id": "b02a", "beat": "b02", "sentences": [4, 4], "mode": "th"},
            {"id": "b03a", "beat": "b03", "sentences": [5, 6], "mode": "vo"},
            {"id": "b03c", "beat": "b03", "sentences": [8, 8], "mode": "vo"},
            {"id": "b04", "beat": "b04", "mode": "th"},
        ]
        d["cues"] = []
        d["judgement_calls"] = []
    errs = d_errors(chain, m)
    for want in ["b01: mixes the unsplit ID with sub-beats",
                 "b02a: a beat split into one piece should just be b02",
                 "b03: sub-beats must be lettered b03a, b03b",
                 "b03c: sentences 8-8 don't follow on from sentence 6"]:
        assert any(want in e for e in errs), (want, errs)


def test_sub_id_must_trace_to_parent(chain):
    def m(d):
        d["segments"][4]["beat"] = "b03"
    errs = d_errors(chain, m)
    assert any("b04: beat is b03 but the ID traces to b04" in e for e in errs)


def test_director_subbeats_must_reach_end(chain):
    def m(d):
        d["segments"][3]["sentences"] = [7, 7]
    errs = d_errors(chain, m)
    assert any("b03: sub-beats cover up to sentence 7, beat ends at 8" in e
               for e in errs)


def test_vo_segment_needs_exactly_one_bed(chain):
    def no_bed(d):
        d["cues"] = []
    assert any("b03b: VO segment has no bed" in e
               for e in d_errors(chain, no_bed))

    def two_beds(d):
        d["cues"].append({"id": "b03.br1", "kind": "br", "placement": "bed",
                          "anchor": {"sentence": 8}, "brief": "second bed"})
    assert any("b03b: VO segment has 2 beds (b03.sr2, b03.br1)" in e
               for e in d_errors(chain, two_beds))


def test_unsplit_vo_beat_needs_bed(chain):
    def m(d):
        d["segments"][3:4] = []
        d["segments"][2] = {"id": "b03", "beat": "b03", "mode": "vo"}
        d["segments"][3]["mode"] = "vo"   # b04 becomes VO with no bed
        d["cues"] = []
        d["judgement_calls"] = []
    errs = d_errors(chain, m)
    assert any("b04: VO segment has no bed" in e for e in errs)


def test_director_cue_rules(chain):
    def m(d):
        d["cues"] = [
            {"id": "b03.sr1", "kind": "sr", "placement": "bed",
             "anchor": {"sentence": 7}, "brief": "collides"},
            {"id": "b03.lt5", "kind": "lt", "placement": "overlay",
             "layer": "overlay", "anchor": {"sentence": 7}, "brief": "not a bed"},
            {"id": "b03.br1", "kind": "br", "placement": "bed",
             "brief": "no anchor"},
            {"id": "b01.br1", "kind": "br", "placement": "bed",
             "anchor": {"sentence": 1}, "brief": "not in a VO sub-beat"},
        ]
    errs = d_errors(chain, m)
    for want in ["b03.sr1: collides with a paper-edit cue",
                 "b03.lt5: the director may only add bed cues",
                 "b03.br1: director cues need a sentence anchor",
                 "b01.br1: anchor sentence 1 lands on b01, not a VO sub-beat"]:
        assert any(want in e for e in errs), (want, errs)


def test_director_cue_next_free_number(chain):
    def m(d):
        d["cues"][0]["id"] = "b03.sr1"
    def pe(p):
        p["beats"][2]["cues"][1]["id"] = "b03.sr3"
    errs = d_errors(chain, m, pe)
    # b03.sr1 no longer collides but isn't after the paper edit's sr3
    assert any("b03.sr1: use the next free number after the paper edit's "
               "b03.sr3" in e for e in errs)


def test_th_bed_needs_explicit_duration(chain):
    def m(d):
        d["segments"][2]["mode"] = "th"   # paper-edit bed b03.sr1 lands on TH
        d["segments"][3]["mode"] = "vo"
        d["cues"][0]["anchor"] = {"sentence": 7}
    errs = d_errors(chain, m)
    assert any("b03.sr1: bed lands on talking-head segment b03a" in e
               for e in errs)


def test_judgement_call_unknown_segment(chain):
    def m(d):
        d["judgement_calls"] = [{"segment": "b07", "note": "?"}]
    assert any("judgement_calls: unknown segment b07" in e
               for e in d_errors(chain, m))


def test_director_reports_bad_paper_edit(chain):
    def pe(p):
        p["beats"][3]["sentences"] = [9, 10]
    errs = d_errors(chain, None, pe)
    assert errs and all(e.startswith("[mini.paper-edit.json]") for e in errs)


# --- reanchor ---------------------------------------------------------------

def th_first_split(d):
    """b03a becomes TH, so the paper-edit bed b03.sr1 (sentence 5) lands on
    a talking-head sub-beat. The director drops its own bed and moves
    b03.sr1 into the VO sub-beat instead."""
    d["segments"][2]["mode"] = "th"
    d["cues"] = []
    d["reanchor"] = [{"cue": "b03.sr1", "from": {"sentence": 5},
                      "to": {"sentence": 7, "phrase": "progress bar"},
                      "reason": "b03a went to camera; the screen starts at b03b"}]


def test_reanchor_moves_bed_into_vo_subbeat(chain):
    assert d_errors(chain, th_first_split) == []


def test_without_reanchor_the_same_split_fails(chain):
    def m(d):
        th_first_split(d)
        d.pop("reanchor")
    errs = d_errors(chain, m)
    assert any("b03.sr1: bed lands on talking-head segment b03a" in e
               for e in errs)
    assert any("b03b: VO segment has no bed" in e for e in errs)


def test_reanchor_rules(chain):
    def m(d):
        th_first_split(d)
        d["cues"] = [{"id": "b03.sr2", "kind": "sr", "placement": "bed",
                      "anchor": {"sentence": 8}, "brief": "director bed"}]
        d["reanchor"] += [
            {"cue": "b03.sr1", "from": {"sentence": 5},
             "to": {"sentence": 8}, "reason": "twice"},
            {"cue": "b03.lt1", "from": {"sentence": 6, "phrase": "export button"},
             "to": {"sentence": 7}, "reason": "not a bed"},
            {"cue": "b03.sr2", "from": {"sentence": 8},
             "to": {"sentence": 7}, "reason": "director cue"},
            {"cue": "b02.sr1", "from": None, "to": {"sentence": 4},
             "reason": "doesn't exist"},
        ]
    errs = d_errors(chain, m)
    for want in ["reanchor b03.sr1: listed more than once",
                 "reanchor b03.lt1: only bed cues can be reanchored",
                 "reanchor b03.sr2: only paper-edit cues can be reanchored",
                 "reanchor b02.sr1: no such cue in the paper edit"]:
        assert any(want in e for e in errs), (want, errs)


def test_reanchor_must_record_the_old_anchor(chain):
    def m(d):
        th_first_split(d)
        d["reanchor"][0]["from"] = None
    errs = d_errors(chain, m)
    assert any("reanchor b03.sr1: 'from' is null but the paper edit's anchor "
               "is {\"sentence\": 5}" in e for e in errs)


def test_reanchor_stays_in_parent_beat(chain):
    def m(d):
        th_first_split(d)
        d["reanchor"][0]["to"] = {"sentence": 9}
    errs = d_errors(chain, m)
    assert any("reanchor b03.sr1: new anchor sentence 9 is outside its parent "
               "beat b03 (5-8)" in e for e in errs)


def test_reanchored_phrase_is_still_checked(chain):
    def m(d):
        th_first_split(d)
        d["reanchor"][0]["to"]["phrase"] = "spinning wheel"
    errs = d_errors(chain, m)
    assert any('b03.sr1: phrase "spinning wheel" is not in sentence 7' in e
               for e in errs)


def test_reanchor_needs_a_reason(chain):
    def m(d):
        th_first_split(d)
        d["reanchor"][0]["reason"] = ""
    assert any("reanchor/0/reason" in e for e in d_errors(chain, m))


# --- non-blocking notes and script_cue lists -----------------------------------

def test_lint_notes_unused_script_cues_and_bare_key_points(chain):
    from validate import lint_file
    def m(pe):
        pe["beats"][1]["key_point"] = True            # b02 has no cues
        pe["beats"][2]["cues"][1]["script_cue"] = [1]  # the [Screen: ...] cue
    chain.write_script().write_paper_edit(m)
    assert errors(chain.paper_edit) == []
    notes = lint_file(chain.paper_edit)
    # script cue 0 is [Talking head]: a mode note, never flagged
    assert not any("script cue 0" in n for n in notes)
    assert "b02: key point with no reinforcing cue" in " ".join(notes)
    r = run_script("validate.py", chain.paper_edit)
    assert r.returncode == 0 and "note: b02: key point" in r.stdout


def test_script_cue_index_checked_in_lists(chain):
    def m(pe):
        pe["beats"][2]["cues"][1]["script_cue"] = [1, 7]
    assert any("b03.sr1: script_cue 7 does not exist" in e
               for e in pe_errors(chain, m))


def test_chapter_is_a_beat_property(chain):
    def m(pe):
        pe["sections"] = [{"id": "sec02", "chapter": "1. Demo"}]
    assert any("sections/0" in e and "chapter" in e for e in pe_errors(chain, m))
