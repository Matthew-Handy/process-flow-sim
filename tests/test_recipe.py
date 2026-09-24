"""Tests for the recipe engine."""

import json

import numpy as np
import pytest

from procsim.materials import SI3N4, SILICON, SIO2
from procsim.recipe import (
    OPERATIONS,
    load_recipe,
    material_id,
    recipe_summary,
    recipe_table,
    run_recipe,
)
from procsim.wafer import Wafer


@pytest.fixture
def w():
    return Wafer()


SHORT_FLOW = [
    {"op": "deposit", "material": "oxide", "thickness_nm": 100},
    {"op": "spin_coat", "thickness_nm": 300},
    {"op": "expose", "dose_mj_cm2": 120, "clear_regions": [[0, 1000]]},
    {"op": "develop"},
    {"op": "etch", "chemistry": "CHF3_O2", "time_min": 3},
]


# --- material names ---------------------------------------------------

@pytest.mark.parametrize(
    "name, expected",
    [("oxide", SIO2), ("SiO2", SIO2), ("sio2", SIO2),
     ("nitride", SI3N4), ("Si", SILICON), ("silicon", SILICON)],
)
def test_material_names_and_aliases_resolve(name, expected):
    assert material_id(name) == expected


def test_integer_material_passes_through():
    assert material_id(SIO2) == SIO2


def test_unknown_material_raises():
    with pytest.raises(ValueError, match="unknown material"):
        material_id("unobtainium")


# --- running ----------------------------------------------------------

def test_steps_run_in_order(w):
    run_recipe(w, SHORT_FLOW)
    assert [e["step"] for e in w.history] == [
        "deposition", "spin_coat", "expose", "develop", "etch"
    ]


def test_named_material_reaches_the_operation(w):
    run_recipe(w, [{"op": "deposit", "material": "oxide",
                    "thickness_nm": 100}])
    assert w.thickness_of(SIO2)[0] == pytest.approx(100.0, abs=w.dz)


def test_named_materials_in_an_etch_rate_table(w):
    run_recipe(w, [
        {"op": "deposit", "material": "oxide", "thickness_nm": 200},
        {"op": "etch", "rates_nm_min": {"sio2": 50}, "time_min": 2},
    ])
    assert w.thickness_of(SIO2)[0] == pytest.approx(100.0, abs=w.dz)


def test_callback_fires_once_per_step(w):
    seen = []
    run_recipe(w, SHORT_FLOW,
               on_step=lambda i, op, wf: seen.append((i, op)))
    assert seen == [(1, "deposit"), (2, "spin_coat"), (3, "expose"),
                    (4, "develop"), (5, "etch")]


def test_comment_keys_are_ignored(w):
    run_recipe(w, [{"op": "deposit", "material": "oxide",
                    "thickness_nm": 100, "comment": "pad oxide"}])
    assert w.thickness_of(SIO2)[0] > 0.0


# --- errors -----------------------------------------------------------

def test_missing_op_raises(w):
    with pytest.raises(ValueError, match="no 'op' key"):
        run_recipe(w, [{"material": "oxide"}])


def test_unknown_operation_lists_the_valid_ones(w):
    with pytest.raises(ValueError, match="unknown operation") as excinfo:
        run_recipe(w, [{"op": "sputter_gold"}])
    for name in OPERATIONS:
        assert name in str(excinfo.value)


def test_bad_parameter_names_the_step(w):
    with pytest.raises(TypeError, match="step 2"):
        run_recipe(w, [
            {"op": "deposit", "material": "oxide", "thickness_nm": 100},
            {"op": "deposit", "material": "oxide", "thikness_nm": 100},
        ])


# --- files ------------------------------------------------------------

def test_load_json_recipe(tmp_path):
    path = tmp_path / "flow.json"
    path.write_text(json.dumps({"steps": SHORT_FLOW}))
    assert load_recipe(path) == SHORT_FLOW


def test_load_bare_list_recipe(tmp_path):
    path = tmp_path / "flow.json"
    path.write_text(json.dumps(SHORT_FLOW))
    assert load_recipe(path) == SHORT_FLOW


def test_load_yaml_recipe():
    steps = load_recipe("recipes/locos_isolation.yaml")
    assert steps[0]["op"] == "oxidize"
    assert all("op" in step for step in steps)


# --- reporting --------------------------------------------------------

def test_recipe_table_has_one_row_per_step(w):
    run_recipe(w, SHORT_FLOW)
    table = recipe_table(w)
    assert len(table) == len(SHORT_FLOW)
    assert list(table["step"]) == [1, 2, 3, 4, 5]
    assert "operation" in table.columns
    assert "time_min" in table.columns


# --- integration ------------------------------------------------------

def test_locos_flow_grows_field_oxide_and_protects_active_areas():
    w = Wafer()
    run_recipe(w, load_recipe("recipes/locos_isolation.yaml"))

    oxide = w.thickness_of(SIO2)
    assert oxide.max() > 400.0        # thick field oxide grew
    assert oxide.min() < 60.0         # active areas kept only pad oxide
    assert w.thickness_of(SI3N4).max() == 0.0   # pad fully stripped
    assert np.ptp(w.surface_profile_nm()) > 100.0   # recessed isolation


def test_recipe_summary_is_one_line_per_step(w):
    run_recipe(w, SHORT_FLOW)
    lines = recipe_summary(w).splitlines()
    assert len(lines) == len(SHORT_FLOW)
    assert lines[0].startswith(" 1. deposition")


def test_recipe_summary_names_materials_instead_of_numbers(w):
    run_recipe(w, [{"op": "deposit", "material": "nitride",
                    "thickness_nm": 100}])
    assert "material=Si3N4" in recipe_summary(w)
    assert "material=3" not in recipe_summary(w)
