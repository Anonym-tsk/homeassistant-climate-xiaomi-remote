 
"""The Xiaomi IR Climate integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import storage
from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Xiaomi IR Climate from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize storage for this specific entry
    store = storage.Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
    hass.data[DOMAIN][entry.entry_id] = {"store": store}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
