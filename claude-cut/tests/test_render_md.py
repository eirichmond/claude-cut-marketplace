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
    assert "### Demo (chapter: 1. Demo)" in md
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
