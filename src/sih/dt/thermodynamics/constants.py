from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThermodynamicConstants:
    """Configurable generic constants for the Stage 1 0-D model.

    These values are engineering placeholders for a generic aero piston engine,
    not specifications or calibration data for a particular UAV engine.
    """

    air_gas_constant_j_kg_k: float = 287.05
    fuel_density_kg_l: float = 0.74
    stoichiometric_air_fuel_ratio: float = 14.7
    displacement_l: float = 2.0
    volumetric_efficiency: float = 0.80
    four_stroke: bool = True

    def __post_init__(self) -> None:
        if self.air_gas_constant_j_kg_k <= 0.0:
            raise ValueError("air gas constant must be positive")
        if self.fuel_density_kg_l <= 0.0:
            raise ValueError("fuel density must be positive")
        if self.stoichiometric_air_fuel_ratio <= 0.0:
            raise ValueError("stoichiometric air-fuel ratio must be positive")
        if self.displacement_l <= 0.0:
            raise ValueError("engine displacement must be positive")
        if not 0.0 < self.volumetric_efficiency:
            raise ValueError("volumetric efficiency must be positive")