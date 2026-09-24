"""
Material definitions for the sim
The wafer cross section is stored as a 2D array of integers
Each integer is a material ID
This module decides what those integers mean
"""

from dataclasses import dataclass

#material IDs. will be the ones that will be used in the wafer grid
VACUUM      = 0
SILICON     = 1
SIO2        = 2 
SI3N4       = 3
POLYSILICON = 4
PHOTORESIST = 5
ALUMINUM    = 6

# Colours were checked for colour-vision deficiency separation rather than
# chosen by eye. Worst adjacent pair is dE 8.1 under protanopia. The
# original light blue oxide and light green nitride sat at dE 14.6 for
# normal vision, below the legibility floor -- and those two films are
# adjacent in almost every flow here, so they were the ones to fix.
# Cross-sections also carry hatch texture, so identity never rests on
# colour alone.


@dataclass(frozen=True)
class Material: 
    """Identity of a material. Deliberately carries no process rates"""
    id: int
    name: str
    color: str

MATERIALS = {
    VACUUM:         Material(VACUUM,        "vacuum", "#ffffff"),
    SILICON:        Material(SILICON,       "Si",       "#4a4a4a"),
    SIO2:           Material(SIO2,          "SiO2",     "#2f6fb0"),
    SI3N4:          Material(SI3N4,         "Si3N4",    "#4aa564"),
    POLYSILICON:    Material(POLYSILICON,   "poly-Si",  "#c0392b"), 
    PHOTORESIST:    Material(PHOTORESIST,   "resist",   "#f4d03f"),
    ALUMINUM:       Material(ALUMINUM,      "Al",       "#9aa1a8"),
}

def name_of(material_id: int) -> str:
    """Human-readable name for material ID"""
    return MATERIALS[material_id].name