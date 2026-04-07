"""Button platform for Tatenergosbyt - кнопки переподключения и отправки показаний."""

import datetime
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the button platform."""
    client = hass.data[DOMAIN][entry.entry_id]

    buttons = []

    # Кнопка переподключения (общая)
    buttons.append(TatenergosbytReconnectButton(client, hass, entry))

    # Получаем данные всех счётчиков для создания кнопок отправки
    readings = await client.get_meter_readings()
    _LOGGER.debug("Creating submit buttons from readings: %s", readings)

    # Кнопки отправки для каждого счётчика
    if isinstance(readings, dict) and "error" not in readings:
        for meter_id, meter_data in readings.items():
            if isinstance(meter_data, dict) and "guid" in meter_data:
                buttons.append(TatenergosbytSubmitButton(client, hass, entry, meter_id, meter_data))
                _LOGGER.info("Created submit button for %s", meter_data.get("service_name"))

    async_add_entities(buttons)

    # Добавляем button-объекты в общий список entities (на всякий случай)
    if "entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entities"] = []
    hass.data[DOMAIN]["entities"].extend(buttons)
    _LOGGER.debug("Total buttons added: %d and added to global entities list", len(buttons))


class TatenergosbytReconnectButton(ButtonEntity):
    """Button to force reconnection to Tatenergosbyt."""

    def __init__(self, client, hass, entry):
        """Initialize the reconnect button."""
        self.client = client
        self.hass = hass
        self._entry = entry
        self._attr_name = "Татенергосбыт Переподключиться"
        self._attr_unique_id = f"tatenergosbyt_reconnect_{entry.entry_id}"
        self._attr_icon = "mdi:refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Transfer of meter readings to Tatenergosbyt",
            manufacturer="Tatenergosbyt",
            model="API Integration",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Reconnect button pressed - forcing reauthentication")

        # Сбрасываем токен
        self.client.auth_token = None

        # Пробуем переавторизоваться
        if await self.client.authenticate():
            _LOGGER.debug("Successfully reauthenticated")

            # Обновляем все сенсоры
            await self.hass.data[DOMAIN][self._entry.entry_id].get_meter_readings()

            # Принудительно обновляем состояние
            for entity in self.hass.data[DOMAIN].get("entities", []):
                if hasattr(entity, "async_update"):
                    await entity.async_update()

            # Записываем событие в историю
            self.hass.bus.async_fire(
                "tatenergosbyt_reconnected", {"success": True, "message": "Successfully reconnected to Tatenergosbyt"}
            )
        else:
            _LOGGER.error("Failed to reauthenticate")
            self.hass.bus.async_fire(
                "tatenergosbyt_reconnected", {"success": False, "message": "Failed to reconnect to Tatenergosbyt"}
            )


class TatenergosbytSubmitButton(ButtonEntity):
    """Button to submit reading for a specific meter."""

    def __init__(self, client, hass, entry, meter_id, data):
        """Initialize the submit button."""
        self.client = client
        self.hass = hass
        self._entry = entry
        self.meter_id = meter_id
        self._guid = data.get("guid")
        self._zone = data.get("zone")

        # Название услуги для отображения
        self._service_name = data.get("service_name", "Unknown")
        clean_name = self._service_name.replace(" - ", " ").strip()

        self._attr_name = f"Татенергосбыт {clean_name} (отправить)"
        self._attr_unique_id = f"tatenergosbyt_submit_{meter_id}"
        self._attr_icon = "mdi:send-check"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Transfer of meter readings to Tatenergosbyt",
            manufacturer="Tatenergosbyt",
            model="API Integration",
        )

    def _can_submit_today(self) -> bool:
        """Check if today is within submission period (15-25)."""
        today = datetime.datetime.now()
        return 15 <= today.day <= 25

    @property
    def available(self) -> bool:
        """Button is only available from 15th to 25th of each month."""
        return self._can_submit_today()

    async def async_press(self) -> None:
        """Handle submit button press."""
        if not self._can_submit_today():
            _LOGGER.warning("Cannot submit %s - outside allowed period (15-25)", self._service_name)
            self.hass.bus.async_fire(
                "tatenergosbyt_notification",
                {
                    "title": "Ошибка отправки",
                    "message": f"Показания для {self._service_name} можно отправлять только с 15 по 25 число",
                    "level": "warning",
                },
            )
            return

        _LOGGER.info("Submitting reading for %s", self._service_name)

        # Ищем number entity для этого счётчика
        number_entity = None
        for entity in self.hass.data[DOMAIN].get("entities", []):
            if hasattr(entity, "meter_id") and entity.meter_id == self.meter_id:
                number_entity = entity
                _LOGGER.warning(
                    "✅ Найден number entity: %s",
                    entity.entity_id if hasattr(entity, "entity_id") else entity
                )
                break

        if not number_entity:
            _LOGGER.error("No number entity found for meter %s", self.meter_id)
            self.hass.bus.async_fire(
                "tatenergosbyt_notification",
                {"title": "Ошибка", "message": f"Не найдено поле ввода для {self._service_name}", "level": "error"},
            )
            return

        # Получаем значение из pending_value
        if hasattr(number_entity, "pending_value"):
            value_to_submit = number_entity.pending_value
            _LOGGER.warning("📦 Использую pending_value: %s", value_to_submit)
        elif hasattr(number_entity, "_pending_value"):
            value_to_submit = number_entity._pending_value
            _LOGGER.warning("📦 Использую _pending_value: %s", value_to_submit)
        else:
            _LOGGER.error("number_entity не имеет pending_value! Атрибуты: %s", dir(number_entity))
            self.hass.bus.async_fire(
                "tatenergosbyt_notification",
                {"title": "Ошибка", "message": "Техническая ошибка: нет pending_value", "level": "error"},
            )
            return

        # Проверяем, что значение не меньше последнего показания
        last_value = number_entity._last_value if hasattr(number_entity, "_last_value") else 0
        if value_to_submit < last_value:
            _LOGGER.warning("Value %s is less than last reading %s", value_to_submit, last_value)
            self.hass.bus.async_fire(
                "tatenergosbyt_notification",
                {
                    "title": "Ошибка валидации",
                    "message": f"Новое показание ({value_to_submit}) не может быть меньше предыдущего ({last_value})",
                    "level": "error",
                },
            )
            return

        # Отправляем показание
        result = await self.client.set_indication(guid=self._guid, value=value_to_submit, zone=self._zone)

        if result.get("success"):
            _LOGGER.info("✅ Successfully submitted %s for %s", value_to_submit, self._service_name)

            # Обновляем сенсоры
            for entity in self.hass.data[DOMAIN].get("entities", []):
                if hasattr(entity, "async_update"):
                    await entity.async_update()

            self.hass.bus.async_fire(
                "tatenergosbyt_notification",
                {
                    "title": "Показания отправлены",
                    "message": f"{self._service_name}: {value_to_submit} {number_entity.native_unit_of_measurement}",
                    "level": "success",
                },
            )
        else:
            error_msg = result.get("message", "Неизвестная ошибка")
            _LOGGER.error("❌ Failed to submit reading: %s", error_msg)
            self.hass.bus.async_fire(
                "tatenergosbyt_notification", {"title": "Ошибка отправки", "message": error_msg, "level": "error"}
            )
