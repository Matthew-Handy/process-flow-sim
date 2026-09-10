# Semiconductor Process Flow Simulator

A physically motivated simulator of the sequence of operations that turns a bare
silicon wafer into a patterned semiconductor structure.

Rather than treating fabrication as a set of unrelated calculations, this project
represents the wafer as a **physical state** that is mutated by each process step.
A recipe is an ordered list of operations — oxidation, deposition, lithography,
development, etching, implantation, CMP — and each one modifies the wafer's
material layers, thicknesses, and dimensions. After every step the simulator can
render a cross-section, so you can watch the structure evolve.

## Scope

The models here are deliberately simplified but physically transparent: Deal-Grove
oxidation kinetics, rate-times-time deposition, selectivity-based etching with a
directionality parameter, Gaussian implant profiles. The goal is to make the
*physics of process integration* visible, not to replicate a commercial TCAD tool.
Where an assumption replaces real physics, the code says so explicitly.

## Status

Under active development. See `docs/roadmap.md`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the tests

```bash
pytest
```

## Author

Matthew Handy — Nanoengineering, Rose-Hulman Institute of Technology
