"""Config flow for Xiaomi IR Climate."""
import logging
import asyncio
import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_REMOTE_ENTITY,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_TARGET_TEMP_STEP,
    CONF_HVAC_MODES,
    CONF_FAN_MODES,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
)

_LOGGER = logging.getLogger(__name__)

HVAC_MODES_LIST = ["cool", "heat", "dry", "fan_only", "auto", "off"]
FAN_MODES_LIST = ["auto", "low", "medium", "high"]

class XiaomiIRClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Xiaomi IR Climate."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup."""
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)

        data_schema = vol.Schema({
            vol.Required("name", default="Air Conditioner"): str,
            vol.Required(CONF_REMOTE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="remote")
            ),
            vol.Required(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): int,
            vol.Required(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): int,
            vol.Required(CONF_TARGET_TEMP_STEP, default=1): int,
            vol.Required(CONF_HVAC_MODES, default=["cool", "heat", "off"]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=HVAC_MODES_LIST,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Required(CONF_FAN_MODES, default=["auto", "low", "medium", "high"]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=FAN_MODES_LIST,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
        })

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return XiaomiIRClimateOptionsFlow(config_entry)


class XiaomiIRClimateOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow (The Learning UI)."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry
        self.codes = {}
        self._last_mode = "cool"
        self._last_fan = "auto"
        self._last_temp = 24
        self._captured_code = None

    async def async_step_init(self, user_input=None):
        """Load existing codes."""
        self.codes = {}
        try:
            if DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
                store_data = self.hass.data[DOMAIN][self.config_entry.entry_id]
                loaded = await store_data["store"].async_load()
                if loaded:
                    self.codes = loaded
        except Exception as e:
            _LOGGER.error(f"Failed to load options flow: {e}")
        
        return await self.async_step_add_code()

    async def async_step_add_code(self, user_input=None, error=None):
        """Unified form to trigger learn OR save code."""
        errors = {}
        description = "Select settings. Check 'Trigger Learning' to start, OR paste a code to save."
        
        # 1. Defaults
        default_hvac = self._last_mode
        default_fan = self._last_fan
        default_temp = self._last_temp
        default_code = self._captured_code if self._captured_code else ""
        
        # Clear capture after using it
        if self._captured_code:
            description = "Success! Code captured automatically. Click Submit to save."
            self._captured_code = None

        if error:
            description = f"NOTE: {error}"

        if user_input is not None:
            self._last_mode = user_input["hvac_mode"]
            self._last_fan = user_input.get("fan_mode", "auto")
            self._last_temp = user_input.get("temperature", 24)

            # --- BRANCH 1: TRIGGER LEARNING ---
            if user_input.get("trigger_learn"):
                remote_entity = self.config_entry.data[CONF_REMOTE_ENTITY]
                
                # Send the learn command FIRST
                try:
                    await self.hass.services.async_call(
                        "xiaomi_miio", "remote_learn_command", 
                        {"entity_id": remote_entity}, blocking=False
                    )
                except Exception:
                    try:
                        await self.hass.services.async_call(
                            "remote", "xiaomi_miio_learn_command", 
                            {"entity_id": remote_entity}, blocking=False
                        )
                    except Exception:
                        pass

                # Start the "Scanner Loop" (Max 30 seconds)
                found_code = None
                for i in range(30):
                    await asyncio.sleep(1) # Wait 1 second
                    
                    # SCANNER: Look inside hass.data for active notifications
                    # This bypasses the Event Bus entirely
                    notifications = self.hass.data.get("persistent_notification", {})
                    
                    # Handle different HA versions (sometimes it's a dict, sometimes an object)
                    if hasattr(notifications, "get"):
                        # It's a dict-like object
                        all_notifs = notifications.get("notifications", {}) 
                        # Sometimes it is just the dict itself
                        if not all_notifs and isinstance(notifications, dict):
                            all_notifs = notifications
                    else:
                        all_notifs = {}

                    # iterate over all active notifications
                    for notif_id, notif in all_notifs.items():
                        message = notif.get("message", "")
                        
                        # CLEANUP: Remove spaces/newlines to make Regex easier
                        clean_msg = message.replace("\n", "").replace(" ", "")
                        
                        # MATCH: Look for 'mk' or 'Z6' followed by base64 chars
                        match = re.search(r'(mk[a-zA-Z0-9+/=]{20,})', clean_msg)
                        if not match:
                             match = re.search(r'(Z6[a-zA-Z0-9+/=]{20,})', clean_msg)
                        
                        if match:
                            found_code = match.group(1)
                            # Cleanup: Dismiss this notification so it doesn't confuse us later
                            await self.hass.services.async_call(
                                "persistent_notification", "dismiss", 
                                {"notification_id": notif_id}, blocking=False
                            )
                            break # Break the inner loop
                    
                    if found_code:
                        break # Break the outer wait loop

                if found_code:
                    self._captured_code = found_code
                    return await self.async_step_add_code(None, error=None)
                else:
                    return await self.async_step_add_code(None, error="Timed out. Notification not found or format not recognized.")
            
            # --- BRANCH 2: SAVE CODE ---
            else:
                code = user_input.get("ir_code")
                if not code:
                    errors["base"] = "missing_code"
                else:
                    mode = user_input["hvac_mode"]
                    if mode not in self.codes: self.codes[mode] = {}
                    if isinstance(self.codes[mode], str): self.codes[mode] = {} 

                    if mode == "off":
                        self.codes["off"] = code
                    else:
                        fan = user_input.get("fan_mode", "auto")
                        temp = str(user_input.get("temperature"))
                        if fan not in self.codes[mode]: self.codes[mode][fan] = {}
                        self.codes[mode][fan][temp] = code

                    if DOMAIN in self.hass.data and self.config_entry.entry_id in self.hass.data[DOMAIN]:
                        await self.hass.data[DOMAIN][self.config_entry.entry_id]["store"].async_save(self.codes)
                        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    
                    return await self.async_step_add_code(None, error="Code Saved! Ready for next.")

        # --- DRAW FORM ---
        hvac_modes = self.config_entry.data.get(CONF_HVAC_MODES, ["off", "cool"])
        fan_modes = self.config_entry.data.get(CONF_FAN_MODES, ["auto"])
        min_temp = self.config_entry.data.get(CONF_MIN_TEMP, 16)
        max_temp = self.config_entry.data.get(CONF_MAX_TEMP, 30)

        schema = vol.Schema({
            vol.Required("hvac_mode", default=self._last_mode): vol.In(hvac_modes),
            vol.Optional("fan_mode", default=self._last_fan): vol.In(fan_modes),
            vol.Optional("temperature", default=self._last_temp): vol.All(vol.Coerce(int), vol.Range(min=min_temp, max=max_temp)),
            vol.Optional("trigger_learn", default=False): bool,
            vol.Optional("ir_code", default=default_code): str,
        })

        return self.async_show_form(
            step_id="add_code", 
            data_schema=schema, 
            errors=errors,
            description_placeholders={"info": description}
        )
