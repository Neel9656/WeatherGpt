from datetime import datetime
from typing import Any


class NWPService:
    """Interface for future GFS, WRF, and ECMWF integrations."""

    async def get_model_forecast(
        self,
        model: str,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        raise NotImplementedError(
            f"NWP model '{model}' is not configured. Connect an official model data source first."
        )