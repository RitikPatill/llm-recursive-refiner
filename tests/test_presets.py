import pytest

from llm_recursive_refiner.presets import PRESETS, Preset, get_preset


def test_all_presets_have_system_prompt():
    for preset in PRESETS.values():
        assert isinstance(preset.system_prompt, str)
        assert len(preset.system_prompt) > 0


def test_all_presets_have_critique_rubric():
    for preset in PRESETS.values():
        assert isinstance(preset.critique_rubric, str)
        assert len(preset.critique_rubric) > 0


def test_get_preset_known():
    p = get_preset("improve-essay")
    assert isinstance(p, Preset)
    assert p.name == "improve-essay"


def test_get_preset_unknown_raises():
    with pytest.raises(ValueError, match="nonexistent"):
        get_preset("nonexistent")
