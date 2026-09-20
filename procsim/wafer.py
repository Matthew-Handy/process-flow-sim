"""
The wafer state is a 2D cross-section that every process step mutates
"""

import copy
import numpy as np

from procsim.materials import VACUUM, SILICON

class Wafer:
    """
    A 2D cross-section of a wafer. The grid is indexed [row, col]. 
    Row 0 is the top if the simulated domain and row index increases downward. Column 0 is the left edge. 
    Heights are in nanometers measured from the original silicon surface.
    pos upward: z = 0 is the starting surface, deposited flims are at pos z and trenches etched in reach negative Z
    """

    def __init__(self, width_nm: float = 2000.0, substrate_thickness_nm: float = 500.0, headroom_nm: float = 1000.0, dx: float = 2.0, dz: float = 2.0,):
        self.width_nm = float(width_nm)
        self.substrate_thickness_nm = float(substrate_thickness_nm)
        self.headroom_nm = float(headroom_nm)
        self.dx = float(dx)
        self.dz = float(dz)

        self.n_cols = int(round(self.width_nm / self.dx))
        self.n_rows = int(round((self.headroom_nm + self.substrate_thickness_nm) / self.dz))

        self.grid = np.full((self.n_rows, self.n_cols), VACUUM, dtype=np.uint8)

        #every row with a center that lies below z = 0 starts as silicon
        
        first_substrate_row = int(round(self.headroom_nm / self.dz))
        self.grid[first_substrate_row:, :] = SILICON

        self.history = []
        self.latent_image = None

    def __repr__(self):
        return (f"Wafer({self.width_nm:.0f} nm wide, "
                f"grid {self.n_rows}x{self.n_cols} @ dx={self.dx} dz={self.dz} nm, "
                f"{len(self.history)} steps)"
        )

    # cord conversion
    def z_of_row(self, row):
        """Height in nm at the center of the 'row'. Accepts an int or an array"""
        return self.headroom_nm - (np.asarray(row) + 0.5) * self.dz

    def row_of_z(self, z_nm):
        """Index of the row containing height 'z_nm', clipped to the domain"""
        row = np.floor((self.headroom_nm - np.asarray(z_nm)) / self.dz)
        return np.clip(row, 0, self.n_rows -1).astype(int)

    def n_rows_for(self, thickness_nm):
        """How many whole rows a thickness spans"""
        return int(round(thickness_nm / self.dz))

    #State queries
    def surface_rows(self):
        """Row index of the topmost non-vacuum cell in each column.
        Returns an array of length n_cols. completely empty column reports 'n_rows', 
        meaning "no materials in this column".
        """
        occupied = self.grid != VACUUM
        first = np.argmax(occupied, axis=0)
        return np.where(occupied.any(axis=0), first, self.n_rows)

    def surface_profile_nm(self):
        """Height of the top surface in each column in nm"""
        return self.z_of_row(self.surface_rows() - 0.5)

    def thickness_of(self, material_id):
        """Total thickness of 'material_id' in each column in nm"""
        return (self.grid == material_id).sum(axis=0) * self.dz

    def log(self, step_name, **params):
        """Record a process step and the parameters it ran with"""
        self.history.append({"step": step_name, "params": params})

    def copy(self):
        """A fully independent duplicate. Nothing is shared with the original"""
        return copy.deepcopy(self)
    