# Roadmap

Build order. Each step leaves the project in a working, testable state.

| # | Step | Adds | Status |
|---|------|------|--------|
| 1 | Wafer + material data structure | The state everything else mutates | done |
| 2 | Deposition | Adding material (conformal and directional) | done |
| 3 | Thermal oxidation | Deal-Grove kinetics; oxide *consumes* silicon | done |
| 4 | Lithography | Resist coat, expose through a mask, develop | done |
| 5 | Etching | Removal with rate, selectivity, and directionality | done |
| 6 | Ion implantation | Gaussian dopant profile, masked by overlying films | |
| 7 | CMP | Planarization, not just removal | done |
| 8 | Recipe engine | Ordered operations loaded from a file | done |
| 9 | Cross-section visualization | A picture after every step | done |
| 10 | Process variability | Stochastic rates, nonuniformity, tool offsets | |
| 11 | Link to Project 1 | Aerial image from the lithography simulator drives exposure | |
| 12 | Metrology outputs | Thickness, CD, sidewall angle, step height | |
| 13 | Statistics and yield | Monte Carlo over a recipe, spec limits, Cp/Cpk | |

## Design commitments

- **One length unit: nanometers.** Every dimension, rate, and parameter in the
  codebase is in nm (or nm/s). Conversions happen only at the user interface.
- **Material identity lives in the registry; process rates do not.** An etch rate
  is a property of a material *and a chemistry*, not of the material alone.
- **Assumptions are labelled.** Where a simplification replaces real physics, the
  docstring says which physics was dropped and when the approximation fails.
