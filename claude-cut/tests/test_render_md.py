import pytest

from render_md import render


def test_render_paper_edit(chain):
    chain.build()
    md = render(chain.paper_edit)
    assert md.startswith("# Paper edit: Mini test video")
    assert "Don't edit this file" in md
    # spoken text comes from the numbered script, verbatim
    assert "Welcome back to the channel. Today we fix the edit. Fine." in md
    assert "**b03**<br>s5–8" in md
    assert "`b03.lt1` LT, to \"progress bar\" at \"export button\": Export" in md
    assert "### Demo" in md and "**Chapter: 1. Demo**" in md
    # inserts push the estimated timecode: b01 starts after the 2s sting
    assert "| **b01**<br>s1–3 | 0:02 |" in md


def test_render_director(chain):
    chain.build()
    md = render(chain.director)
    assert "**3 talking head segments" in md and "2 voiceover segments" in md
    th, vo = md.split("## 2. Voiceover shot list")
    assert "**b01**" in th and "**b03a**" not in th
    assert "**b03a**" in vo and "> Open the settings panel on the left. " \
                                "Click the export button at the bottom." in vo
    assert "*Bed:* `b03.sr1`" in vo and "*Bed:* `b03.sr2`" in vo
    assert "| 3 | b03a | VO | Demo | 14 |" in md
    assert "- **b03b.** could be TH" in md


def test_render_refuses_invalid(chain):
    chain.build(d_mutate=lambda d: d.update(cues=[]))
    with pytest.raises(SystemExit) as e:
        render(chain.director)
    assert "does not validate" in str(e.value)


def test_render_director_shows_reanchors(chain):
    from test_validate import th_first_split
    chain.build(d_mutate=th_first_split)
    md = render(chain.director)
    assert "## 5. Reanchored beds" in md
    assert ("| `b03.sr1` | sentence 5 | sentence 7 at \"progress bar\" | b03b | "
            "b03a went to camera; the screen starts at b03b |") in md
    vo = md.split("## 2. Voiceover shot list")[1].split("## 3.")[0]
    assert "*Bed:* `b03.sr1`" in vo and "(reanchored, see below)" in vo


def test_render_director_shows_retime(chain):
    from test_validate import keep_b03_on_camera
    chain.build(d_mutate=keep_b03_on_camera)
    md = render(chain.director)
    assert ('| `b03.sr1` | sentence 5, whole segment | sentence 5, to '
            '"export button" | b03 |') in md
