from __future__ import annotations

from dataclasses import dataclass
import math

from sih.dt.thermodynamics.atmosphere import air_density
from sih.dt.thermodynamics.constants import ThermodynamicConstants


@dataclass(frozen=True)
class ThermodynamicState:
    """Stage 1 thermodynamic estimates with descriptive SI units."""

    air_density_kg_m3: float
    air_mass_flow_kg_s: float
    fuel_mass_flow_kg_s: float
    air_fuel_ratio: float
    equivalence_ratio: float


class ThermodynamicModel:
    """Engine-agnostic, deterministic 0-D intake and mixture calculator."""

    def __init__(self, constants: ThermodynamicConstants | None = None) -> None:
        self.constants = constants or ThermodynamicConstants()

    def calculate(
        self,
        *,
        manifold_absolute_pressure_kpa: float,
        intake_air_temperature_c: float,
        rpm: float,
        fuel_flow_l_h: float,
    ) -> ThermodynamicState:
        """Calculate mass-flow and mixture estimates from telemetry quantities."""
        values = (
            manifold_absolute_pressure_kpa,
            intake_air_temperature_c,
            rpm,
            fuel_flow_l_h,
        )
        if any(not math.isfinite(value) for value in values):
            raise ValueError("thermodynamic inputs must be finite")
        if manifold_absolute_pressure_kpa <= 0.0:
            raise ValueError("absolute manifold pressure must be positive")
        if intake_air_temperature_c < -273.15:
            raise ValueError("intake air temperature is below absolute zero")
        if rpm < 0.0:
            raise ValueError("rpm must be non-negative")
        if fuel_flow_l_h < 0.0:
            raise ValueError("fuel flow must be non-negative")

        temperature_k = intake_air_temperature_c + 273.15
        density = air_density(
            pressure_pa=manifold_absolute_pressure_kpa * 1000.0,
            temperature_k=temperature_k,
            gas_constant_j_kg_k=self.constants.air_gas_constant_j_kg_k,
        )

        # A four-stroke engine inducts its displacement once every two revolutions.
        cycles_per_second = rpm / (120.0 if self.constants.four_stroke else 60.0)
        air_volume_flow_m3_s = (
            self.constants.displacement_l / 1000.0
        ) * cycles_per_second * self.constants.volumetric_efficiency
        air_mass_flow = density * air_volume_flow_m3_s
        fuel_mass_flow = fuel_flow_l_h * self.constants.fuel_density_kg_l / 3600.0

        if fuel_mass_flow == 0.0 or air_mass_flow == 0.0:
            # Ratios are undefined at zero flow; retain finite state values.
            air_fuel_ratio = 0.0
            equivalence_ratio = 0.0
        else:
            air_fuel_ratio = air_mass_flow / fuel_mass_flow
            equivalence_ratio = self.constants.stoichiometric_air_fuel_ratio / air_fuel_ratio

        return ThermodynamicState(
            air_density_kg_m3=density,
            air_mass_flow_kg_s=air_mass_flow,
            fuel_mass_flow_kg_s=fuel_mass_flow,
            air_fuel_ratio=air_fuel_ratio,
            equivalence_ratio=equivalence_ratio,
        )