"""Every skill has front matter, and every script, template and reference a
skill tells the agent to use exists."""
import re

import pytest
import yaml

from conftest import ROOT

SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_skill_front_matter_and_references(skill):
    text = skill.read_text()
    fm = yaml.safe_load(text.split("---")[1])
    assert fm["name"] == skill.parent.name
    assert len(fm["description"]) > 80
    for script in set(re.findall(r"(?:\$S|scripts)/([a-z_]+\.py)", text)):
        assert (ROOT / "scripts" / script).exists(), script
    for mjs in set(re.findall(r"graphics/([a-z]+\.mjs)", text)):
        assert (ROOT / "graphics" / mjs).exists(), mjs
    for ref in set(re.findall(r"references/([a-z-]+\.md)", text)):
        assert (skill.parent / "references" / ref).exists(), ref


def test_graphics_skill_templates_exist():
    text = (ROOT / "skills" / "graphics" / "SKILL.md").read_text()
    named = set(re.findall(r"`(chapterCard|lowerThird|keyTerm|tag|callout|warningStrip|"
                           r"slideAcross)`", text))
    have = {p.stem for p in (ROOT / "graphics" / "templates").glob("*.mjs")}
    assert named and named <= have
    assert have - named == set(), "a template the skill doesn't mention"


def test_produce_command_names_real_scripts_and_skills():
    cmd = ROOT / "commands" / "produce.md"
    text = cmd.read_text()
    fm = yaml.safe_load(text.split("---")[1])
    assert fm["description"] and fm["argument-hint"]
    for script in set(re.findall(r"([a-z_]+\.py)", text)):
        assert (ROOT / "scripts" / script).exists(), script
    for skill in set(re.findall(r"the `([a-z-]+)` skill", text)):
        assert (ROOT / "skills" / skill / "SKILL.md").exists(), skill
    import pipeline
    for stage in pipeline.STAGES:
        assert f"**{stage}**" in text, stage            # every stage is covered
