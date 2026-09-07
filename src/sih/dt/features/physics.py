from __future__ import annotations
from sih.dt.core.state import EngineState

class PhysicsExpectedState:
    """Expected physical values for an engine state under normal conditions."""
    def __init__(self, state: EngineState):
        self.timestamp = state.timestamp
        # Very simplified physical baseline model for demonstration.
        # In reality, this would use rpm/throttle/etc to compute expected values.
        base_load = state.throttle_ratio if state.throttle_ratio > 0 else 0.5
        
        self.egt = 610.0 + (50.0 * base_load)
        self.cht = 150.0 + (20.0 * base_load)
        self.oil_pressure = 40.0 + (10.0 * base_load)
        self.oil_temperature = 90.0 + (15.0 * base_load)
        self.fuel_flow = 15.0 * base_load
        self.vibration = 0.9 + (0.5 * base_load)

class PhysicsReferenceModel:
    """Generates expected EngineStates based on operating conditions."""
    
    def expected_state(self, state: EngineState) -> PhysicsExpectedState:
        """Return the expected physical values for the given state."""
        return PhysicsExpectedState(state)
