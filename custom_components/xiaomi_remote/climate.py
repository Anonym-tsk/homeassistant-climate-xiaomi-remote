import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_AUTO, HVAC_MODE_OFF,
    FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO,
    ATTR_HVAC_MODE, ATTR_HVAC_MODES, ATTR_MAX_TEMP, ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_STEP, ATTR_FAN_MODE, ATTR_FAN_MODES,
    ATTR_PRESET_MODE, ATTR_PRESET_MODES,
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_FAN_MODE, SUPPORT_PRESET_MODE)
from homeassistant.components.remote import (
    ATTR_COMMAND, DOMAIN, SERVICE_SEND_COMMAND)
from homeassistant.const import (
    ATTR_TEMPERATURE, ATTR_ENTITY_ID, CONF_NAME, CONF_CUSTOMIZE,
    STATE_UNAVAILABLE, STATE_UNKNOWN)
from homeassistant.core import callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

CONF_REMOTE = 'remote'
CONF_TEMP_SENSOR = 'temp_sensor'
CONF_POWER_TEMPLATE = 'power_template'
CONF_TARGET_TEMP = 'target_temp'
CONF_COMMANDS = 'commands'

DEFAULT_NAME = 'Xiaomi Remote Climate'
DEFAULT_MIN_TEMP = 16
DEFAULT_MAX_TEMP = 32
DEFAULT_TARGET_TEMP = 24
DEFAULT_TARGET_TEMP_STEP = 1
DEFAULT_HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_AUTO]
DEFAULT_FAN_MODES = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
DEFAULT_PRESET_MODES = []
DEFAULT_HVAC_MODE = HVAC_MODE_OFF
DEFAULT_FAN_MODE = FAN_AUTO
DEFAULT_PRESET_MODE = None

ATTR_LAST_HVAC_MODE = 'last_hvac_mode'
ATTR_LAST_FAN_MODE = 'last_fan_mode'
ATTR_LAST_PRESET_MODE = 'last_preset_mode'
ATTR_SUPPORTED_FEATURES = 'supported_features'

COMMAND_POWER_OFF = 'off'
COMMAND_PRESET_MODES = 'presets'

CUSTOMIZE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_HVAC_MODES): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_FAN_MODES): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_PRESET_MODES): vol.All(cv.ensure_list, [cv.string])
})

COMMANDS_SCHEMA = vol.Schema({
    vol.Required(COMMAND_POWER_OFF): cv.string
}, extra=vol.ALLOW_EXTRA)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_REMOTE): cv.entity_id,
    vol.Optional(CONF_TEMP_SENSOR): cv.entity_id,
    vol.Optional(CONF_POWER_TEMPLATE): cv.template,
    vol.Optional(ATTR_MIN_TEMP, default=DEFAULT_MIN_TEMP): cv.positive_int,
    vol.Optional(ATTR_MAX_TEMP, default=DEFAULT_MAX_TEMP): cv.positive_int,
    vol.Optional(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): cv.positive_int,
    vol.Optional(ATTR_TARGET_TEMP_STEP, default=DEFAULT_TARGET_TEMP_STEP): cv.positive_int,
    vol.Optional(ATTR_HVAC_MODE, default=DEFAULT_HVAC_MODE): cv.string,
    vol.Optional(ATTR_FAN_MODE, default=DEFAULT_FAN_MODE): cv.string,
    vol.Optional(ATTR_PRESET_MODE, default=DEFAULT_PRESET_MODE): vol.Maybe(cv.string),
    vol.Optional(CONF_CUSTOMIZE, default={}): CUSTOMIZE_SCHEMA,
    vol.Required(CONF_COMMANDS): COMMANDS_SCHEMA
})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the xiaomi remote climate platform."""
    name = config.get(CONF_NAME)
    remote_entity_id = config.get(CONF_REMOTE)
    commands = config.get(CONF_COMMANDS)

    min_temp = config.get(ATTR_MIN_TEMP)
    max_temp = config.get(ATTR_MAX_TEMP)
    target_temp = config.get(CONF_TARGET_TEMP)
    target_temp_step = config.get(ATTR_TARGET_TEMP_STEP)
    hvac_modes = config.get(CONF_CUSTOMIZE).get(ATTR_HVAC_MODES, []) or DEFAULT_HVAC_MODES
    fan_modes = config.get(CONF_CUSTOMIZE).get(ATTR_FAN_MODES, []) or DEFAULT_FAN_MODES
    preset_modes = config.get(CONF_CUSTOMIZE).get(ATTR_PRESET_MODES, []) or DEFAULT_PRESET_MODES
    default_hvac_mode = config.get(ATTR_HVAC_MODE)
    default_fan_mode = config.get(ATTR_FAN_MODE)
    default_preset_mode = config.get(ATTR_PRESET_MODE)

    temp_entity_id = config.get(CONF_TEMP_SENSOR)
    power_template = config.get(CONF_POWER_TEMPLATE)

    async_add_entities([
        RemoteClimate(hass, name, remote_entity_id, commands, min_temp, max_temp, target_temp, target_temp_step,
                      hvac_modes, fan_modes, preset_modes, default_hvac_mode, default_fan_mode, default_preset_mode,
                      temp_entity_id, power_template)
    ])


class RemoteClimate(ClimateDevice, RestoreEntity):
    def __init__(self, hass, name, remote_entity_id, commands, min_temp, max_temp, target_temp, target_temp_step,
                 hvac_modes, fan_modes, preset_modes, default_hvac_mode, default_fan_mode, default_preset_mode,
                 temp_entity_id, power_template):
        """Representation of a Xiaomi Remote Climate device."""

        self.hass = hass
        self._name = name
        self._remote_entity_id = remote_entity_id
        self._commands = commands

        self._min_temp = min_temp
        self._max_temp = max_temp
        self._target_temperature = target_temp
        self._target_temperature_step = target_temp_step
        self._unit_of_measurement = hass.config.units.temperature_unit

        self._current_temperature = None
        self._default_hvac_mode = default_hvac_mode
        self._current_hvac_mode = default_hvac_mode
        self._last_hvac_mode = default_hvac_mode
        self._default_fan_mode = default_fan_mode
        self._current_fan_mode = default_fan_mode
        self._last_fan_mode = default_fan_mode
        self._default_preset_mode = default_preset_mode
        self._current_preset_mode = default_preset_mode
        self._last_preset_mode = default_preset_mode

        self._temp_entity_id = temp_entity_id
        self._power_template = power_template

        self._hvac_modes = hvac_modes
        self._fan_modes = fan_modes
        self._preset_modes = preset_modes

        self._support_flags = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE
        if preset_modes:
            self._support_flags |= SUPPORT_PRESET_MODE
        self._enabled_flags = self._support_flags

        if temp_entity_id:
            async_track_state_change(hass, temp_entity_id, self._async_temp_changed)

        if power_template:
            power_template.hass = hass
            power_entity_ids = power_template.extract_entities()
            async_track_state_change(hass, power_entity_ids, self._async_power_changed)

    async def _async_temp_changed(self, entity_id, old_state, new_state):
        """Update current temperature."""
        if new_state is None or new_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            return

        self._async_update_temp(new_state)
        await self.async_update_ha_state()

    @callback
    def _async_update_temp(self, state):
        """Update temperature with latest state from sensor."""
        try:
            self._current_temperature = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)

    async def _async_power_changed(self, entity_id, old_state, new_state):
        """Update current power."""
        if new_state is None:
            return

        self._async_update_power()
        await self.async_update_ha_state()

    @callback
    def _async_update_power(self):
        """Update power with latest state from template."""
        try:
            if self._power_template.async_render().lower() not in ('true', 'on', '1'):
                self._current_hvac_mode = HVAC_MODE_OFF
            else:
                self._current_hvac_mode = self._last_hvac_mode
        except TemplateError as ex:
            _LOGGER.warning('Unable to update power from template: %s', ex)

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return self._current_temperature

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._max_temp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._target_temperature_step

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool."""
        return self._current_hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_modes

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self._current_fan_mode

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return self._fan_modes

    @property
    def preset_mode(self):
        """Return the current preset mode."""
        return self._current_preset_mode

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return self._preset_modes

    @property
    def state_attributes(self):
        """Return the optional state attributes."""
        data = super().state_attributes
        data[ATTR_LAST_HVAC_MODE] = self._last_hvac_mode
        data[ATTR_LAST_FAN_MODE] = self._last_fan_mode
        data[ATTR_LAST_PRESET_MODE] = self._last_preset_mode
        return data

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._enabled_flags

    @property
    def is_on(self):
        """Return true if on."""
        return self._current_hvac_mode != HVAC_MODE_OFF

    def _update_flags_get_command(self):
        """Update supported features list."""
        if not self.is_on:
            command = self._commands[COMMAND_POWER_OFF]
        else:
            hvac_mode = self._current_hvac_mode.lower()
            fan_mode = self._current_fan_mode.lower()
            temp = int(self._target_temperature)

            try:
                if isinstance(self._commands[hvac_mode], str):
                    command = self._commands[hvac_mode]
                    self._enabled_flags = self._support_flags ^ SUPPORT_TARGET_TEMPERATURE ^ SUPPORT_FAN_MODE
                elif isinstance(self._commands[hvac_mode][fan_mode], str):
                    command = self._commands[hvac_mode][fan_mode]
                    self._enabled_flags = self._support_flags ^ SUPPORT_TARGET_TEMPERATURE
                else:
                    command = self._commands[hvac_mode][fan_mode][temp]
                    self._enabled_flags = self._support_flags
            except KeyError:
                command = None
                _LOGGER.error('Could not find command for %s/%s/%s', hvac_mode, fan_mode, temp)

        return command

    def _send_command(self):
        """Send IR code to device."""
        command = self._update_flags_get_command()
        if command is not None:
            self.hass.services.call(DOMAIN, SERVICE_SEND_COMMAND, {
                ATTR_COMMAND: 'raw:' + command,
                ATTR_ENTITY_ID: self._remote_entity_id
            })

    def _send_command_preset(self):
        """Send IR code for preset to device."""
        preset_mode = COMMAND_POWER_OFF
        if self._current_preset_mode is not None:
            preset_mode = self._current_preset_mode.lower()
        try:
            command = self._commands[COMMAND_PRESET_MODES][preset_mode]
            self.hass.services.call(DOMAIN, SERVICE_SEND_COMMAND, {
                ATTR_COMMAND: 'raw:' + command,
                ATTR_ENTITY_ID: self._remote_entity_id
            })
        except KeyError:
            _LOGGER.error('Could not find command for %s/%s', COMMAND_PRESET_MODES, preset_mode)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            self._target_temperature = kwargs.get(ATTR_TEMPERATURE)
            if self.is_on:
                self._send_command()
            self.schedule_update_ha_state()

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        self._current_fan_mode = fan_mode
        self._last_fan_mode = fan_mode
        if self.is_on:
            self._send_command()
        self.schedule_update_ha_state()

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._current_hvac_mode = hvac_mode
        if hvac_mode != HVAC_MODE_OFF:
            self._last_hvac_mode = hvac_mode
        self._send_command()
        self.schedule_update_ha_state()

    def set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        self._current_preset_mode = preset_mode
        self._last_preset_mode = preset_mode
        if self.is_on:
            self._send_command_preset()
        self.schedule_update_ha_state()

    def turn_on(self):
        """Turn device on."""
        self.set_hvac_mode(self._last_hvac_mode)

    def turn_off(self):
        """Turn device off."""
        self.set_hvac_mode(HVAC_MODE_OFF)

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()

        if state is not None:
            self._last_hvac_mode = state.attributes.get(ATTR_LAST_HVAC_MODE, self._default_hvac_mode)
            self._current_hvac_mode = state.attributes.get(ATTR_HVAC_MODE, self._last_hvac_mode)
            self._last_fan_mode = state.attributes.get(ATTR_LAST_FAN_MODE, self._default_fan_mode)
            self._current_fan_mode = state.attributes.get(ATTR_FAN_MODE, self._last_fan_mode)
            self._last_preset_mode = state.attributes.get(ATTR_LAST_PRESET_MODE, self._default_preset_mode)
            self._current_preset_mode = state.attributes.get(ATTR_PRESET_MODE, self._last_preset_mode)
            self._target_temperature = state.attributes.get(ATTR_TEMPERATURE, self._target_temperature)

            enabled_flags = state.attributes.get(ATTR_SUPPORTED_FEATURES, self._enabled_flags)
            if enabled_flags <= SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE | SUPPORT_PRESET_MODE:
                self._enabled_flags = enabled_flags

        if self._temp_entity_id:
            temp_state = self.hass.states.get(self._temp_entity_id)
            if temp_state and temp_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
                self._async_update_temp(temp_state)

        if self._power_template:
            self._async_update_power()

        self._update_flags_get_command()
        await self.async_update_ha_state(True)
