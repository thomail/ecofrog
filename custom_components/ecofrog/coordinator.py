"""Coordinator for WS66i."""
from __future__ import annotations

from datetime import datetime, timedelta
import json
import logging

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EcoFrogUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="ecofrog",
            update_interval=timedelta(seconds=POLL_INTERVAL),
        )
        self.entry = entry

    def _update_ecofrog(self):
        """Fetch data for each of the zones."""
        REQ = {
            "DeviceRequest": {
                "Username": self.entry.data["username"],
                "Email": self.entry.data["email"],
                "SecurityStamp": self.entry.data["securitystamp"],
                "DeviceID": self.entry.data["deviceid"],
            }
        }

        URL = "http://aes-gate-ecofrog.azurewebsites.net/Api/FuncDevice"

        with requests.post(URL, json=REQ) as r:
            data = r.json()
            # _LOGGER.debug("--- ECOFROG RESULT IN: " + r.text)
            # The E-sensorix API has a bug and double-encodes
            # JSON. Fix it, but anticipate their own eventual
            # fix. (maybe)
            if type(data) == str:
                try:
                    data = json.loads(data)["DeviceResponse"]
                    _LOGGER.debug(
                        "Worked around EcoFrog doubly-encoded JSON: %s", str(data)
                    )

                except json.JSONDecodeError as e:
                    if "login" in data.casefold():
                        raise ConfigEntryAuthFailed(data) from e
                    _LOGGER.error("E-sensorix API said: %s", data)

                    raise UpdateFailed from e

                except Exception as e:
                    raise UpdateFailed from e

            else:
                data = data["DeviceResponse"]

            # Massage the data a little. Assume the array can have multiple
            # entries, even though that's not documented in EcoFrog docs (and
            # neither is the existence of the array in the JSON output!)
            for datum in data:
                datum["last_update_successful"] = True
                try:
                    datum["last_update"] = datetime.strptime(
                        datum["LastUpdate"], "%m/%d/%Y %I:%M:%S %p"
                    )
                except (ValueError, KeyError):
                    datum["last_update_successful"] = False

            _LOGGER.debug("Coordinator data out: %s", data)
            return data

        return data

    async def _async_update_data(self):
        """Fetch data for each of the zones."""
        # The data that is returned here can be accessed through coordinator.data.
        return await self.hass.async_add_executor_job(self._update_ecofrog)


# End of file.
