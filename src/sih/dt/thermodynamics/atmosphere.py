from __future__ import annotations


def air_density(
    pressure_pa: float,
    temperature_k: float,
    gas_constant_j_kg_k: float = 287.05,
) -> float:
    """Return dry-air density in kg/m^3 using absolute pressure and temperature."""
    if pressure_pa <= 0.0:
        raise ValueError("absolute pressure must be positive")
    if temperature_k <= 0.0:
        raise ValueError("absolute temperature must be positive")
    if gas_constant_j_kg_k <= 0.0:
        raise ValueError("air gas constant must be positive")
    return pressure_pa / (gas_constant_j_kg_k * temperature_k)