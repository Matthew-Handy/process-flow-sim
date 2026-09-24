"""Cross-section rendering.

The point of a cross-section is to let someone look at a wafer and see
what happened to it, so these figures follow a few rules:

  * Material identity never rests on colour alone. Every material also
    carries a hatch texture and appears in the legend, so the figure
    survives colour-vision deficiency, greyscale printing and
    projector washout.
  * Only materials actually present are listed. A legend full of
    absent entries makes the reader hunt.
  * Axes are in nanometres with z = 0 at the original silicon surface,
    matching the coordinate system the rest of the code uses.
  * Empty headroom is cropped away, so the structure fills the frame
    instead of floating in a sea of vacuum.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

from procsim.materials import MATERIALS, VACUUM

# Texture is the secondary encoding that makes the figure readable
# without colour. Densities differ as well as direction so the
# materials stay distinct in greyscale.
HATCHES = {
    VACUUM: "",
    1: "",        # silicon: the substrate, left plain as the ground
    2: "///",     # SiO2
    3: "xxx",     # Si3N4
    4: "...",     # poly-Si
    5: "\\\\\\",  # resist
    6: "|||",     # Al
}

_MATERIAL_IDS = sorted(MATERIALS)
_CMAP = ListedColormap([MATERIALS[i].color for i in _MATERIAL_IDS])
_NORM = BoundaryNorm([i - 0.5 for i in _MATERIAL_IDS] + [_MATERIAL_IDS[-1] + 0.5],
                     _CMAP.N)


def _z_limits(wafer, margin_nm):
    """Crop to the material, with a margin, so vacuum does not dominate."""
    occupied = wafer.grid != VACUUM
    if not occupied.any():
        return -wafer.substrate_thickness_nm, wafer.headroom_nm

    rows = np.flatnonzero(occupied.any(axis=1))
    top = float(wafer.z_of_row(rows[0] - 0.5)) + margin_nm
    bottom = max(float(wafer.z_of_row(rows[-1] + 0.5)),
                 -wafer.substrate_thickness_nm)
    # Always show a slice of substrate for context.
    bottom = min(bottom, -100.0)
    return bottom, min(top, wafer.headroom_nm)


def cross_section(wafer, ax=None, *, title=None, margin_nm=100.0,
                  hatch=True, legend=True, z_range=None):
    """Draw the wafer cross-section. Returns the axes.

    `z_range` forces an explicit (bottom, top) window. Panels in a
    sequence must share one, or the reader compares heights against
    silently different scales.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 3.6))

    bottom, top = z_range if z_range is not None else _z_limits(wafer, margin_nm)
    extent = (0.0, wafer.width_nm, bottom, top)

    row_top = int(wafer.row_of_z(top))
    row_bottom = int(wafer.row_of_z(bottom))
    window = wafer.grid[row_top:row_bottom + 1, :]

    ax.imshow(window, cmap=_CMAP, norm=_NORM, extent=extent,
              origin="upper", aspect="auto", interpolation="nearest")

    present = [m for m in _MATERIAL_IDS
               if m != VACUUM and (wafer.grid == m).any()]

    if hatch:
        x = np.linspace(0.0, wafer.width_nm, window.shape[1])
        z = np.linspace(top, bottom, window.shape[0])
        for material in present:
            pattern = HATCHES.get(material, "")
            if not pattern:
                continue
            ax.contourf(x, z, (window == material).astype(float),
                        levels=[0.5, 1.5], colors="none",
                        hatches=[pattern], alpha=0.0)

    # A faint rule at the original silicon surface: the datum every
    # thickness in the process history is measured against.
    ax.axhline(0.0, color="#00000055", linewidth=0.8, linestyle=(0, (4, 3)),
               zorder=3)

    ax.set_xlabel("Lateral position (nm)")
    ax.set_ylabel("Height above original Si surface (nm)")
    ax.set_xlim(0.0, wafer.width_nm)
    ax.set_ylim(bottom, top)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#00000033")
    ax.tick_params(colors="#444444", labelsize=9)

    if title:
        ax.set_title(title, fontsize=11, loc="left", color="#222222", pad=8)

    if legend and present:
        handles = [
            Patch(facecolor=MATERIALS[m].color, edgecolor="#00000044",
                  hatch=HATCHES.get(m, "") if hatch else None,
                  label=MATERIALS[m].name)
            for m in present
        ]
        ax.legend(handles=handles, loc="upper left",
                  bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=9)

    return ax


def surface_profile(wafer, ax=None, *, title=None):
    """Plot the topography: surface height against lateral position."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 2.2))

    x = (np.arange(wafer.n_cols) + 0.5) * wafer.dx
    ax.plot(x, wafer.surface_profile_nm(), color="#2f6fb0", linewidth=2.0)
    ax.axhline(0.0, color="#00000055", linewidth=0.8, linestyle=(0, (4, 3)))

    ax.set_xlabel("Lateral position (nm)")
    ax.set_ylabel("Surface height (nm)")
    ax.set_xlim(0.0, wafer.width_nm)
    ax.grid(True, color="#00000014", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#00000033")
    ax.tick_params(colors="#444444", labelsize=9)

    if title:
        ax.set_title(title, fontsize=11, loc="left", color="#222222", pad=8)

    return ax


def save_cross_section(wafer, path, *, title=None, dpi=150, **kwargs):
    """Render one cross-section straight to a file."""
    fig, ax = plt.subplots(figsize=(9, 3.6))
    cross_section(wafer, ax=ax, title=title, **kwargs)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def flow_figure(wafer, steps, *, run, ncols=2, dpi=150, path=None,
                suptitle=None):
    """Run a recipe and draw a panel per step, including the start.

    `run` is the recipe runner, passed in rather than imported so this
    module stays independent of the recipe engine.
    """
    panels = [("start", wafer.copy())]

    def capture(index, operation, wf):
        panels.append((f"{index}. {operation}", wf.copy()))

    run(wafer, steps, on_step=capture)

    # One z window for every panel. Small multiples on different scales
    # invite the reader to compare heights that are not comparable.
    limits = [_z_limits(s, 100.0) for _, s in panels]
    z_range = (min(b for b, _ in limits), max(t for _, t in limits))

    # Some steps change the wafer's chemistry without changing its shape.
    # Exposure is the obvious one: it writes a latent image and leaves the
    # cross-section identical. Say so, rather than letting the panel look
    # like a mistake.
    labelled = []
    for index, (label, snapshot) in enumerate(panels):
        if index and np.array_equal(snapshot.grid, panels[index - 1][1].grid):
            label += "  (no change to the structure)"
        labelled.append((label, snapshot))
    panels = labelled

    nrows = int(np.ceil(len(panels) / ncols))
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(7.5 * ncols, 2.9 * nrows),
                             squeeze=False, sharex=True, sharey=True)

    for ax, (label, snapshot) in zip(axes.flat, panels):
        cross_section(snapshot, ax=ax, title=label, legend=False,
                      z_range=z_range)
        ax.set_xlabel("")
        ax.set_ylabel("")

    for ax in axes.flat[len(panels):]:
        ax.set_visible(False)

    present = sorted({m for _, s in panels for m in _MATERIAL_IDS
                      if m != VACUUM and (s.grid == m).any()})
    handles = [Patch(facecolor=MATERIALS[m].color, edgecolor="#00000044",
                     hatch=HATCHES.get(m, ""), label=MATERIALS[m].name)
               for m in present]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles),
               frameon=False, fontsize=10, bbox_to_anchor=(0.5, -0.01))

    fig.supxlabel("Lateral position (nm)", fontsize=10, color="#444444")
    fig.supylabel("Height above original Si surface (nm)", fontsize=10,
                  color="#444444")

    if suptitle:
        fig.suptitle(suptitle, fontsize=13, y=1.0)

    fig.tight_layout()
    if path is not None:
        fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
    return fig
