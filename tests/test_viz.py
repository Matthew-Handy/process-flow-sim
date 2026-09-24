"""Tests for cross-section rendering.

These are mostly structural. A figure cannot be asserted to "look
right", but it can be asserted to contain the right things, to share
one scale across panels, and not to raise.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

from procsim.deposition import deposit
from procsim.materials import MATERIALS, SI3N4, SILICON, SIO2, VACUUM
from procsim.recipe import run_recipe
from procsim.viz import (
    HATCHES,
    cross_section,
    flow_figure,
    save_cross_section,
    surface_profile,
)
from procsim.wafer import Wafer


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


@pytest.fixture
def w():
    wafer = Wafer()
    deposit(wafer, SIO2, thickness_nm=200.0)
    return wafer


SHORT_FLOW = [
    {"op": "deposit", "material": "nitride", "thickness_nm": 100},
    {"op": "spin_coat", "thickness_nm": 300},
    {"op": "expose", "dose_mj_cm2": 120, "clear_regions": [[0, 1000]]},
    {"op": "develop"},
]


def test_every_material_has_a_hatch_defined():
    assert set(HATCHES) == set(MATERIALS)


def test_cross_section_returns_axes(w):
    assert cross_section(w) is not None


def test_legend_lists_only_materials_present(w):
    ax = cross_section(w)
    labels = {text.get_text() for text in ax.get_legend().get_texts()}
    assert labels == {"Si", "SiO2"}
    assert "resist" not in labels


def test_vacuum_is_never_in_the_legend(w):
    ax = cross_section(w)
    labels = {text.get_text() for text in ax.get_legend().get_texts()}
    assert "vacuum" not in labels


def test_explicit_z_range_is_honoured(w):
    ax = cross_section(w, z_range=(-300.0, 500.0))
    assert ax.get_ylim() == (-300.0, 500.0)


def test_x_axis_spans_the_wafer(w):
    ax = cross_section(w)
    assert ax.get_xlim() == (0.0, w.width_nm)


def test_empty_wafer_does_not_raise():
    wafer = Wafer()
    wafer.grid[:, :] = VACUUM
    cross_section(wafer)


def test_surface_profile_plots_one_line(w):
    ax = surface_profile(w)
    assert len(ax.lines) >= 1


def test_save_writes_a_file(w, tmp_path):
    path = tmp_path / "section.png"
    save_cross_section(w, path, title="test")
    assert path.exists() and path.stat().st_size > 0


# --- flow figures -----------------------------------------------------

def test_flow_figure_has_a_panel_per_step_plus_the_start():
    fig = flow_figure(Wafer(), SHORT_FLOW, run=run_recipe, ncols=2)
    visible = [ax for ax in fig.axes if ax.get_visible()]
    assert len(visible) == len(SHORT_FLOW) + 1


def test_flow_figure_panels_share_one_scale():
    """Small multiples on different scales invite false comparisons."""
    fig = flow_figure(Wafer(), SHORT_FLOW, run=run_recipe, ncols=2)
    limits = {ax.get_ylim() for ax in fig.axes if ax.get_visible()}
    assert len(limits) == 1


def test_steps_that_change_nothing_visible_are_labelled():
    """Exposure writes a latent image and leaves the structure alone."""
    fig = flow_figure(Wafer(), SHORT_FLOW, run=run_recipe, ncols=2)
    # Panel titles are set with loc="left", which matplotlib keeps in a
    # separate Text object from the centre title.
    titles = [ax.get_title(loc="left") for ax in fig.axes if ax.get_visible()]
    expose_title = next(t for t in titles if "expose" in t)
    assert "no change" in expose_title


def test_flow_figure_writes_a_file(tmp_path):
    path = tmp_path / "flow.png"
    flow_figure(Wafer(), SHORT_FLOW, run=run_recipe, ncols=2, path=path)
    assert path.exists() and path.stat().st_size > 0


def test_flow_figure_leaves_the_wafer_fully_processed():
    w = Wafer()
    flow_figure(w, SHORT_FLOW, run=run_recipe, ncols=2)
    assert [e["step"] for e in w.history] == [
        "deposition", "spin_coat", "expose", "develop"
    ]
