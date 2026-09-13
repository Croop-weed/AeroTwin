from __future__ import annotations

from typing import Annotated
from fastapi import Depends

from sih.dt.api.services.analytics_service import AnalyticsService, get_analytics_service
from sih.dt.api.services.broadcast_service import BroadcastService, get_broadcast_service
from sih.dt.api.services.simulation_service import SimulationService, get_simulation_service
from sih.dt.api.services.twin_service import TwinService, get_twin_service
from sih.dt.api.state.manager import TwinStateManager, get_state_manager

StateManagerDep = Annotated[TwinStateManager, Depends(get_state_manager)]
TwinServiceDep = Annotated[TwinService, Depends(get_twin_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
SimulationServiceDep = Annotated[SimulationService, Depends(get_simulation_service)]
BroadcastServiceDep = Annotated[BroadcastService, Depends(get_broadcast_service)]
