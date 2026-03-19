"""Init for Tatenergosbyt integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TatenergosbytApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Все платформы, которые использует интеграция
PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tatenergosbyt from a config entry."""
    _LOGGER.debug("Setting up entry %s", entry.entry_id)

    hass.data.setdefault(DOMAIN, {})

    # Создаем HTTP сессию и клиент API
    session = async_get_clientsession(hass)
    client = TatenergosbytApiClient(username=entry.data["username"], password=entry.data["password"], session=session)

    # Сохраняем клиента в hass.data
    hass.data[DOMAIN][entry.entry_id] = client

    # Инициализируем хранилище для всех entities (сенсоры, кнопки, числа)
    if "entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entities"] = []

    # Настраиваем все платформы
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(f"Tatenergosbyt integration setup completed for entry {entry.entry_id}")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading entry %s", entry.entry_id)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info(f"Tatenergosbyt integration unloaded for entry {entry.entry_id}")
    return unload_ok


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Tatenergosbyt integration from YAML (if needed)."""
    _LOGGER.debug("Async setup called")
    return True
