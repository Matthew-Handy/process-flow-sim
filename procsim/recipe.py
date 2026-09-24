"""Process recipes: an ordered sequence of operations applied to a wafer.

A recipe is just data -- a list of steps, each naming an operation and
its parameters -- so it can live in a YAML or JSON file, be version
controlled, diffed, and handed to someone else. That is how real
process flows are managed, and it is what makes the rest of this
project reproducible: the recipe defines the run, and the wafer's
history records what actually happened.

Materials may be written as names ("oxide", "SiO2", "nitride") rather
than integer ids, because a recipe file is meant to be read by people.

Example
-------
    steps = [
        {"op": "oxidize", "temperature_c": 1000, "time_min": 20},
        {"op": "spin_coat", "thickness_nm": 400},
        {"op": "expose", "dose_mj_cm2": 120,
         "clear_regions": [[0, 400], [800, 1200]]},
        {"op": "develop"},
        {"op": "etch", "chemistry": "CHF3_O2", "time_min": 4},
        {"op": "etch", "chemistry": "O2_ash", "time_min": 2},
    ]
    run_recipe(wafer, steps)
"""

import json
from pathlib import Path

import pandas as pd

from procsim.cmp import polish
from procsim.deposition import deposit
from procsim.etch import etch
from procsim.lithography import develop, expose, spin_coat
from procsim.materials import MATERIALS, name_of
from procsim.oxidation import oxidize

OPERATIONS = {
    "deposit": deposit,
    "oxidize": oxidize,
    "spin_coat": spin_coat,
    "expose": expose,
    "develop": develop,
    "etch": etch,
    "cmp": polish,
}

# Parameters whose value names a material.
_MATERIAL_PARAMS = ("material", "stop_on")

_ALIASES = {
    "air": "vacuum", "vac": "vacuum",
    "si": "si", "silicon": "si",
    "oxide": "sio2", "sio2": "sio2", "glass": "sio2",
    "nitride": "si3n4", "si3n4": "si3n4",
    "poly": "poly-si", "polysilicon": "poly-si", "poly-si": "poly-si",
    "resist": "resist", "photoresist": "resist", "pr": "resist",
    "al": "al", "aluminium": "al", "aluminum": "al", "metal": "al",
}

_BY_NAME = {material.name.lower(): material.id
            for material in MATERIALS.values()}


def material_id(name):
    """Look up a material id from a name or alias. Ints pass through."""
    if isinstance(name, (int, float)) and not isinstance(name, bool):
        return int(name)
    key = _ALIASES.get(str(name).strip().lower())
    if key is None or key not in _BY_NAME:
        known = ", ".join(sorted(_ALIASES))
        raise ValueError(f"unknown material {name!r}; known names are {known}")
    return _BY_NAME[key]


def _resolve(params):
    """Turn human-written parameter values into what the functions want."""
    resolved = dict(params)

    for key in _MATERIAL_PARAMS:
        if resolved.get(key) is not None:
            resolved[key] = material_id(resolved[key])

    if resolved.get("rates_nm_min") is not None:
        resolved["rates_nm_min"] = {
            material_id(k): float(v)
            for k, v in resolved["rates_nm_min"].items()
        }

    if resolved.get("clear_regions") is not None:
        resolved["clear_regions"] = [
            (float(a), float(b)) for a, b in resolved["clear_regions"]
        ]

    return resolved


def run_recipe(wafer, steps, *, on_step=None):
    """Apply every step in order. Modifies the wafer in place.

    `on_step(index, operation, wafer)` is called after each step, which
    is how a cross-section gets rendered after every operation without
    this module knowing anything about plotting.
    """
    for index, raw in enumerate(steps, start=1):
        if "op" not in raw:
            raise ValueError(f"step {index} has no 'op' key: {raw!r}")

        params = dict(raw)
        operation = params.pop("op")
        params.pop("comment", None)

        if operation not in OPERATIONS:
            known = ", ".join(sorted(OPERATIONS))
            raise ValueError(
                f"step {index}: unknown operation {operation!r}; "
                f"valid operations are {known}"
            )

        try:
            OPERATIONS[operation](wafer, **_resolve(params))
        except TypeError as exc:
            raise TypeError(f"step {index} ({operation}): {exc}") from exc

        if on_step is not None:
            on_step(index, operation, wafer)

    return wafer


def load_recipe(path):
    """Read a recipe from a .yaml/.yml or .json file."""
    path = Path(path)
    text = path.read_text()

    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)

    steps = data["steps"] if isinstance(data, dict) else data
    if not isinstance(steps, list):
        raise ValueError(f"{path} does not contain a list of steps")
    return steps


def recipe_table(wafer):
    """The wafer's process history as a table, one row per step."""
    rows = []
    for index, entry in enumerate(wafer.history, start=1):
        row = {"step": index, "operation": entry["step"]}
        row.update(entry["params"])
        rows.append(row)
    return pd.DataFrame(rows)


_MATERIAL_VALUED = ("material", "stop_on")


def _format_value(key, value):
    if key in _MATERIAL_VALUED:
        return name_of(int(value))
    if key == "rates_nm_min":
        inner = ", ".join(f"{name_of(int(m))}:{r:g}" for m, r in value.items())
        return "{" + inner + "}"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def recipe_summary(wafer):
    """One readable line per step, listing only that step's parameters.

    `recipe_table` is the machine-readable view and is wide and sparse
    because different operations take different parameters. This is the
    one to print, put in a README, or read out loud in a review.
    """
    lines = []
    for index, entry in enumerate(wafer.history, start=1):
        params = ", ".join(
            f"{key}={_format_value(key, value)}"
            for key, value in entry["params"].items()
            if value is not None and value != {}
        )
        lines.append(f"{index:2d}. {entry['step']:<11s} {params}")
    return "\n".join(lines)
