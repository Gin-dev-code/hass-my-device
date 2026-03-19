"""Number platform for Tatenergosbyt - ввод показаний для каждого счётчика."""

import datetime
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up number entities for each meter."""
    client = hass.data[DOMAIN][entry.entry_id]

    # Получаем данные всех счётчиков
    readings = await client.get_meter_readings()
    _LOGGER.debug(f"Creating number inputs from readings: {readings}")

    numbers = []

    if isinstance(readings, dict) and "error" not in readings:
        for meter_id, meter_data in readings.items():
            if isinstance(meter_data, dict) and "guid" in meter_data:
                numbers.append(TatenergosbytIndicationNumber(client, hass, entry, meter_id, meter_data))
                _LOGGER.info(f"Created number input for {meter_data.get('service_name')}")

    async_add_entities(numbers)

    # Добавляем number-объекты в общий список entities для доступа из кнопок
    if "entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entities"] = []
    hass.data[DOMAIN]["entities"].extend(numbers)
    _LOGGER.debug(f"Added {len(numbers)} number entities to global entities list")


class TatenergosbytIndicationNumber(NumberEntity):
    """Number entity for entering meter readings for a specific meter."""

    def __init__(self, client, hass, entry, meter_id, data):
        """Initialize the number input."""
        self.client = client
        self.hass = hass
        self._entry = entry
        self.meter_id = meter_id
        self._guid = data.get("guid")
        self._zone = data.get("zone")

        # Текущее показание (последнее переданное)
        self._last_value = data.get("value", 0)

        # Значение для отправки (изменяемое пользователем)
        self._pending_value = self._last_value

        # Название услуги
        self._service_name = data.get("service_name", "Unknown")
        clean_name = self._service_name.replace(" - ", " ").strip()

        self._attr_name = f"Татенергосбыт {clean_name} (новые показания)"
        self._attr_unique_id = f"tatenergosbyt_number_{meter_id}"

        # Ограничения для ввода
        self._attr_native_min_value = 0
        self._attr_native_max_value = 999999
        self._attr_native_step = 0.01
        self._attr_native_value = float(self._pending_value)
        self._attr_native_unit_of_measurement = data.get("unit", "ед.")

        # Информация об устройстве
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Transfer of meter readings to Tatenergosbyt",
            manufacturer="Tatenergosbyt",
            model="API Integration",
        )

        self._attr_icon = "mdi:pencil"

        # Дополнительные атрибуты
        self._attr_extra_state_attributes = {
            "guid": self._guid,
            "meter_number": data.get("meter_number"),
            "service_name": self._service_name,
            "last_indication": self._last_value,
            "zone": self._zone,
            "can_submit": self._can_submit_today(),
        }

        _LOGGER.debug(f"Number input created: {self._attr_name} with GUID {self._guid}")

    @property
    def pending_value(self):
        """Return the pending value."""
        return self._pending_value

    def _can_submit_today(self) -> bool:
        """Check if today is within submission period (15-25)."""
        today = datetime.datetime.now()
        return 15 <= today.day <= 25

    @property
    def available(self) -> bool:
        """Number input is always available, but submission may be restricted."""
        return True

    async def async_set_native_value(self, value: float) -> None:
        """Update the pending value when user changes it."""
        self._pending_value = value
        self._attr_native_value = value
        self._attr_extra_state_attributes["pending_value"] = value
        _LOGGER.warning(f"⚠️ Пользователь изменил значение {self._service_name} на {value}")

    async def async_update(self):
        """Update the number entity with latest data."""
        readings = await self.client.get_meter_readings()

        if isinstance(readings, dict) and self.meter_id in readings:
            data = readings[self.meter_id]
            self._last_value = data.get("value", 0)
            self._attr_extra_state_attributes.update(
                {"last_indication": self._last_value, "can_submit": self._can_submit_today()}
            )

            # Если пользователь ещё не вводил новое значение, показываем последнее
            if self._pending_value == self._last_value:
                self._attr_native_value = float(self._last_value)
