 
"""Climate platform for Xiaomi IR Climate."""
import logging
import asyncio
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
    CONF_NAME,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    CONF_REMOTE_ENTITY,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_TARGET_TEMP_STEP,
    CONF_HVAC_MODES,
    CONF_FAN_MODES,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup climate entity from config entry."""
    config = config_entry.data
    store_data = hass.data[DOMAIN][config_entry.entry_id]
    store = store_data["store"]

    # Load existing codes from storage
    codes = await store.async_load()
    if codes is None:
        codes = {}

    entity = XiaomiIRClimate(hass, config, codes, store)
    async_add_entities([entity])


class XiaomiIRClimate(ClimateEntity, RestoreEntity):
    """Representation of a Xiaomi IR Climate device."""

    def __init__(self, hass, config, codes, store):
        """Initialize the climate device."""
        self.hass = hass
        self._name = config.get(CONF_NAME)
        self._remote_entity = config.get(CONF_REMOTE_ENTITY)
        self._min_temp = config.get(CONF_MIN_TEMP)
        self._max_temp = config.get(CONF_MAX_TEMP)
        self._target_temp_step = config.get(CONF_TARGET_TEMP_STEP)
        self._attr_hvac_modes = config.get(CONF_HVAC_MODES)
        self._attr_fan_modes = config.get(CONF_FAN_MODES)
        
        self._codes = codes
        self._store = store

        # Current state
        self._hvac_mode = HVACMode.OFF
        self._target_temp = 24
        self._fan_mode = self._attr_fan_modes[0] if self._attr_fan_modes else "auto"
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        )
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._hvac_mode = last_state.state
            self._target_temp = last_state.attributes.get(ATTR_TEMPERATURE, 24)
            # Restore other attributes if needed

    @property
    def name(self):
        return self._name

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def target_temperature(self):
        return self._target_temp

    @property
    def target_temperature_step(self):
        return self._target_temp_step

    @property
    def min_temp(self):
        return self._min_temp

    @property
    def max_temp(self):
        return self._max_temp
    
    async def async_update_codes(self, new_codes):
        """Update the codes dictionary from the Options Flow."""
        self._codes = new_codes
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        self._target_temp = temp
        await self._send_ir_code()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._hvac_mode = hvac_mode
        await self._send_ir_code()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        self._fan_mode = fan_mode
        await self._send_ir_code()
        self.async_write_ha_state()

    async def _send_ir_code(self):
        """Find the code in the dictionary and send it."""
        # Structure: codes[hvac_mode][fan_mode][temp]
        # For OFF, usually just codes['off']
        
        code_to_send = None

        if self._hvac_mode == HVACMode.OFF:
            code_to_send = self._codes.get("off")
        else:
            mode_data = self._codes.get(self._hvac_mode, {})
            # If structure is mode -> fan -> temp
            fan_data = mode_data.get(self._fan_mode, {})
            
            # Handle temperature as string key
            temp_key = str(int(self._target_temp))
            code_to_send = fan_data.get(temp_key)

            # Fallback: if user didn't define fan modes in YAML structure, 
            # maybe they just did mode -> temp (simpler version)
            if not code_to_send and isinstance(fan_data, str):
                 # This handles cases where fan_mode might not be in the tree
                 pass

        if code_to_send:
            if code_to_send.startswith("Raw"):
                # Handle raw format if needed, usually just send the string
                pass
            
            await self.hass.services.async_call(
                "remote",
                "send_command",
                {
                    "entity_id": self._remote_entity,
                    "command": code_to_send
                }
            )
        else:
            _LOGGER.warning(
                f"No IR code found for {self._hvac_mode} - {self._fan_mode} - {self._target_temp}"
            )
