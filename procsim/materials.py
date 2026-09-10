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

@dataclass(frozen=True)
class Material: 
    """Identity of a material. Deliberately carries no process rates"""
    id: int
    name: str
    color: str

MATERIALS = {
    VACUUM:         Material(VACUUM,        "vacuum", "#ffffff"),
    SILICON:        Material(SILICON,       "Si",       "#4a4a4a"),
    SIO2:           Material(SIO2,          "SiO2",     "#7fb3d5"),
    SI3N4:          Material(SI3N4,         "Si3N4",    "#52be80"),
    POLYSILICON:    Material(POLYSILICON,   "poly-Si",    "#c0392b"), 
    PHOTORESIST:    Material(PHOTORESIST,   "resist",     "#f4d03f"),
    ALUMINUM:       Material(ALUMINUM,      "Al",       "#aeb6bf"),
}

def name_of(material_id: int) -> str:
    """Human-readable name for material ID"""
    return MATERIALS[material_id].name