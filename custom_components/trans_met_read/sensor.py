"""Sensor platform for Tatenergosbyt."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id]

    # Получаем показания всех счётчиков
    readings = await client.get_meter_readings()
    _LOGGER.debug("Initial readings: %s", readings)

    sensors = []

    # Если есть ошибка, создаем только сенсор статуса
    if isinstance(readings, dict) and "error" in readings:
        _LOGGER.error(f"Error getting readings: {readings['error']}")
        sensors.append(TatenergosbytStatusSensor(client, hass, entry))
        async_add_entities(sensors)
        return

    # Создаем сенсор для КАЖДОГО найденного счётчика
    if isinstance(readings, dict):
        for meter_id, meter_data in readings.items():
            if isinstance(meter_data, dict) and "service_name" in meter_data:
                sensors.append(TatenergosbytMeterSensor(client, hass, entry, meter_id, meter_data))
                _LOGGER.debug(f"Created sensor for {meter_data.get('service_name')} ({meter_id})")

    # Добавляем сенсор статуса
    sensors.append(TatenergosbytStatusSensor(client, hass, entry))

    # Сохраняем все сенсоры для обновления по кнопке
    if "entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entities"] = []
    hass.data[DOMAIN]["entities"].extend(sensors)

    _LOGGER.info(f"Total sensors created: {len(sensors)}")
    async_add_entities(sensors)


class TatenergosbytMeterSensor(SensorEntity):
    """Representation of a Tatenergosbyt meter sensor."""

    def __init__(self, client, hass, entry, meter_id, data):
        """Initialize the sensor."""
        self.client = client
        self.hass = hass
        self._entry = entry
        self.meter_id = meter_id
        self._guid = data.get("guid")

        # Формируем понятное имя из service_name
        service_name = data.get("service_name", "Unknown")
        # Очищаем название от лишних символов
        clean_name = service_name.replace(" - ", " ").strip()

        self._attr_name = f"Татенергосбыт {clean_name}"
        self._attr_unique_id = f"tatenergosbyt_{meter_id}"
        self._attr_native_unit_of_measurement = data.get("unit", "ед.")
        self._attr_native_value = data.get("value", 0)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Transfer of meter readings to Tatenergosbyt",
            manufacturer="Tatenergosbyt",
            model="API Integration",
        )
        self._attr_icon = self._get_icon_from_service(service_name)

        # Добавляем дополнительные атрибуты
        self._attr_extra_state_attributes = {
            "meter_number": data.get("meter_number"),
            "service_name": data.get("service_name"),
            "address": data.get("address"),
            "tariff": data.get("tariff"),
            "zone": data.get("zone"),
            "guid": data.get("guid"),
            "last_update": data.get("date"),
            "domHoz": data.get("domHoz"),
        }

        _LOGGER.debug(f"Sensor {self._attr_name} created with value {self._attr_native_value}")

    def _get_icon_from_service(self, service_name: str) -> str:
        """Get appropriate icon based on service type."""
        service_lower = service_name.lower()
        if "элект" in service_lower:
            return "mdi:flash"
        if "хвс" in service_lower:
            return "mdi:water"
        if "гвс" in service_lower:
            return "mdi:water-boiler"
        if "газ" in service_lower:
            return "mdi:fire"
        return "mdi:counter"

    async def async_update(self):
        """Update the sensor."""
        readings = await self.client.get_meter_readings()

        if isinstance(readings, dict) and self.meter_id in readings:
            data = readings[self.meter_id]
            self._attr_native_value = data.get("value", 0)
            self._attr_extra_state_attributes.update(
                {
                    "meter_number": data.get("meter_number"),
                    "service_name": data.get("service_name"),
                    "address": data.get("address"),
                    "tariff": data.get("tariff"),
                    "zone": data.get("zone"),
                    "last_update": data.get("date"),
                }
            )
            _LOGGER.debug(f"Updated {self._attr_name} = {self._attr_native_value}")


class TatenergosbytStatusSensor(SensorEntity):
    """Connection status sensor."""

    def __init__(self, client, hass, entry):
        """Initialize the sensor."""
        self.client = client
        self.hass = hass
        self._entry = entry
        self._attr_name = "Татенергосбыт Статус"
        self._attr_unique_id = f"tatenergosbyt_status_{entry.entry_id}"
        self._attr_native_value = "Подключено" if client.auth_token else "Отключено"
        self._attr_icon = "mdi:cloud-check" if client.auth_token else "mdi:cloud-alert"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Transfer of meter readings to Tatenergosbyt",
            manufacturer="Tatenergosbyt",
            model="API Integration",
        )
        self._attr_extra_state_attributes = {"username": client.username, "base_url": client.base_url}

    async def async_update(self):
        """Update the sensor."""
        self._attr_native_value = "Подключено" if self.client.auth_token else "Отключено"
        self._attr_icon = "mdi:cloud-check" if self.client.auth_token else "mdi:cloud-alert"
        self._attr_extra_state_attributes = {"username": self.client.username, "base_url": self.client.base_url}
