async def async_learn_command(hass, entity_id, slot, timeout):
    await hass.services.async_call(
        domain="xiaomi_miio",
        service="remote_learn_command",
        target={"entity_id": entity_id},
        service_data={"slot": slot, "timeout": timeout},
        blocking=True
    )
