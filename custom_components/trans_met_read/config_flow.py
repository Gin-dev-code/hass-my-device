"""Config flow for Tatenergosbyt integration."""

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TatenergosbytApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TransferOfMeterReadingsToTatenergosbytConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tatenergosbyt."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = TatenergosbytApiClient(user_input["username"], user_input["password"], session)

            try:
                if await client.authenticate():
                    return self.async_create_entry(title="Transfer of meter readings to Tatenergosbyt", data=user_input)
                errors["base"] = "invalid_auth"
            except Exception as ex:
                _LOGGER.exception("Unexpected exception: %s", ex)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )
