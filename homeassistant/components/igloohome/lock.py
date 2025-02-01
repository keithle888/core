"""Implementation of the lock platform."""

from datetime import timedelta

from aiohttp import ClientError
from igloohome_api import (
    BRIDGE_JOB_LOCK,
    BRIDGE_JOB_UNLOCK,
    DEVICE_TYPE_LOCK,
    Api as IgloohomeApi,
    ApiException,
    GetDeviceInfoResponse,
)

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IgloohomeConfigEntry
from .entity import IgloohomeBaseEntity
from .utils import get_linked_bridge

# Scan interval set to allow Lock entity update the bridge linked to it.
SCAN_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IgloohomeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lock entities."""
    async_add_entities(
        (
            IgloohomeLockEntity(
                api_device_info=device,
                api=entry.runtime_data.api,
                bridgeId=str(
                    get_linked_bridge(device.deviceId, entry.runtime_data.devices)
                ),
            )
            for device in entry.runtime_data.devices
            if device.type == DEVICE_TYPE_LOCK
            and get_linked_bridge(device.deviceId, entry.runtime_data.devices)
            is not None
        ),
        update_before_add=True,
    )


class IgloohomeLockEntity(IgloohomeBaseEntity, LockEntity):
    """Implementation of a device that has locking capabilities."""

    # Operating on assumed state because there is no API to query the state.
    _attr_assumed_state = True
    _attr_supported_features = LockEntityFeature.OPEN

    def __init__(
        self, api_device_info: GetDeviceInfoResponse, api: IgloohomeApi, bridgeId: str
    ) -> None:
        """Initialize the class."""
        super().__init__(
            api_device_info=api_device_info,
            api=api,
            unique_key="lock",
        )
        self.bridge_id = bridgeId

    async def async_lock(self, **kwargs):
        """Lock this lock."""
        try:
            await self.api.create_bridge_proxied_job(
                self.api_device_info.deviceId, self.bridge_id, BRIDGE_JOB_LOCK
            )
        except (ApiException, ClientError) as err:
            raise HomeAssistantError from err

    async def async_unlock(self, **kwargs):
        """Unlock this lock."""
        try:
            await self.api.create_bridge_proxied_job(
                self.api_device_info.deviceId, self.bridge_id, BRIDGE_JOB_UNLOCK
            )
        except (ApiException, ClientError) as err:
            raise HomeAssistantError from err

    async def async_open(self, **kwargs):
        """Open (unlatch) this lock."""
        try:
            await self.api.create_bridge_proxied_job(
                self.api_device_info.deviceId, self.bridge_id, BRIDGE_JOB_UNLOCK
            )
        except (ApiException, ClientError) as err:
            raise HomeAssistantError from err

    async def async_update(self) -> None:
        """Update the bridge linked to this lock."""
        try:
            devices = await self.api.get_devices()
            linked_bridge_id = get_linked_bridge(
                self.api_device_info.deviceId, devices.payload
            )
            if linked_bridge_id is None:
                self._attr_available = False
            else:
                self._attr_available = True
                self.bridge_id = linked_bridge_id
        except (ApiException, ClientError):
            self._attr_available = False
        else:
            self._attr_available = True
