"""API client for Tatenergosbyt."""

import asyncio
import base64
import logging
from typing import Any

import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)


class TatenergosbytApiClient:
    """API Client for Tatenergosbyt."""

    def __init__(self, username: str, password: str, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.session = session
        self.base_url = "https://lkfl.tatenergosbyt.ru:446"
        self.auth_token = None

    async def _preflight_login(self) -> bool:
        """Send OPTIONS preflight request as browsers do."""
        _LOGGER.debug("Sending OPTIONS preflight request to /Login")
        try:
            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ru,en;q=0.9",
                "Access-Control-Request-Headers": "authorization,authorization-token,content-type",
                "Access-Control-Request-Method": "POST",
                "Origin": "https://lkfl.tatenergosbyt.ru",
                "Referer": "https://lkfl.tatenergosbyt.ru/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36",
            }
            async with async_timeout.timeout(10):
                response = await self.session.options(f"{self.base_url}/Login", headers=headers)
                _LOGGER.debug("Preflight response status: %s", response.status)
                return True
        except Exception as err:
            _LOGGER.warning("Preflight request failed (can be ignored): %s", err)
            return False

    async def authenticate(self) -> bool:
        """Authenticate with Tatenergosbyt."""
        _LOGGER.debug("Authenticating with Tatenergosbyt")

        await self._preflight_login()
        await asyncio.sleep(0.1)

        try:
            async with async_timeout.timeout(30):
                auth_data = {"login": self.username, "password": self.password}

                credentials = f"{self.username}:{self.password}"
                encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
                basic_auth_header = f"Basic {encoded_credentials}"

                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "ru,en;q=0.9",
                    "Authorization": basic_auth_header,
                    "Connection": "keep-alive",
                    "Content-Type": "application/json;charset=UTF-8",
                    "Host": "lkfl.tatenergosbyt.ru:446",
                    "Origin": "https://lkfl.tatenergosbyt.ru",
                    "Referer": "https://lkfl.tatenergosbyt.ru/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36",
                    "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "YaBrowser";v="26.3", "Yowser";v="2.5"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                }

                _LOGGER.debug("Sending POST request to %s/Login", self.base_url)
                response = await self.session.post(f"{self.base_url}/Login", json=auth_data, headers=headers)

                _LOGGER.debug("Response status: %s", response.status)
                _LOGGER.debug("Response headers: %s", dict(response.headers))

                if response.status == 200:
                    self.auth_token = response.headers.get("authorization-token")
                    if self.auth_token:
                        _LOGGER.debug("Successfully authenticated, token received")
                        return True
                    _LOGGER.error("No authorization token in response")
                    return False
                error_body = await response.text()
                _LOGGER.error("Authentication failed with status: %s, body: %s", response.status, error_body[:200])
                return False

        except TimeoutError:
            _LOGGER.error("Timeout connecting to Tatenergosbyt")
            return False
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Tatenergosbyt: %s", err)
            return False
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            return False

    async def get_meter_readings(self) -> dict[str, Any]:
        """
        Получить показания всех счётчиков от Татэнергосбыт.

        Отправляет POST запрос на /CurrentIndication с номером лицевого счета.
        Возвращает словарь, где ключ - номер счётчика, значение - все данные.
        """
        if not self.auth_token:
            _LOGGER.error("Not authenticated")
            if not await self.authenticate():
                return {"error": "Not authenticated"}

        _LOGGER.debug("Fetching meter readings from %s/CurrentIndication", self.base_url)

        try:
            async with async_timeout.timeout(30):
                # Создаем Basic Auth заголовок
                credentials = f"{self.username}:{self.password}"
                encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
                basic_auth = f"Basic {encoded_credentials}"

                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "ru,en;q=0.9",
                    "Authorization": basic_auth,
                    "Authorization-Token": self.auth_token,
                    "Content-Type": "application/json;charset=UTF-8",
                    "Origin": "https://lkfl.tatenergosbyt.ru",
                    "Referer": "https://lkfl.tatenergosbyt.ru/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36",
                    "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "YaBrowser";v="26.3", "Yowser";v="2.5"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                }

                # Отправляем номер лицевого счета в теле запроса
                payload = {
                    "domHoz": self.username  # Важно: именно domHoz!
                }

                _LOGGER.debug("Sending payload: %s", payload)

                response = await self.session.post(f"{self.base_url}/CurrentIndication", json=payload, headers=headers)

                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("RAW API RESPONSE: %s", data)

                    if data.get("success"):
                        readings = {}

                        for idx, item in enumerate(data.get("indication", [])):
                            meter_id = item.get("meterNumber", f"meter_{idx}")

                            readings[meter_id] = {
                                "meter_number": item.get("meterNumber"),
                                "service_name": item.get("serviceName"),
                                "value": float(item.get("lastIndication", 0)) if item.get("lastIndication") else 0,
                                "date": item.get("date"),
                                "unit": self._get_unit_from_service(item.get("serviceName", "")),
                                "tariff": item.get("tariff", [{}])[0].get("value") if item.get("tariff") else None,
                                "address": item.get("address"),
                                "zone": item.get("zone"),
                                "guid": item.get("guid"),
                                "domHoz": item.get("domHoz"),
                            }

                            _LOGGER.debug(
                                "Found meter: %s - %s = %s",
                                meter_id,
                                item.get("serviceName"),
                                item.get("lastIndication")
                            )

                        _LOGGER.info("Total meters found: %d", len(readings))
                        return readings

                    return {"error": data.get("message")}
                _LOGGER.error("Failed to get readings: %s", response.status)
                try:
                    error_body = await response.text()
                    _LOGGER.error("Error body: %s", error_body)
                except:
                    pass
                return {"error": f"HTTP {response.status}"}

        except TimeoutError:
            _LOGGER.error("Timeout fetching readings")
            return {"error": "timeout"}
        except aiohttp.ClientError as err:
            _LOGGER.error("Client error fetching readings: %s", err)
            return {"error": str(err)}
        except Exception as err:
            _LOGGER.error("Unexpected error fetching readings: %s", err)
            return {"error": str(err)}

    async def set_indication(self, guid: str, value: float, zone: str = None) -> dict[str, Any]:
        """
        Отправить показание для конкретного счётчика.

        Args:
            guid: Уникальный идентификатор счётчика
            value: Показание
            zone: Зона (для многотарифных счётчиков)

        Returns:
            Результат отправки
        """
        if not self.auth_token:
            _LOGGER.error("Not authenticated for setting indication")
            if not await self.authenticate():
                return {"success": False, "message": "Not authenticated"}

        _LOGGER.debug("Sending indication for GUID %s: value %s", guid, value)

        try:
            async with async_timeout.timeout(30):
                # Создаем Basic Auth заголовок
                credentials = f"{self.username}:{self.password}"
                encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
                basic_auth = f"Basic {encoded_credentials}"

                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "ru,en;q=0.9",
                    "Authorization": basic_auth,
                    "Authorization-Token": self.auth_token,
                    "Content-Type": "application/json;charset=UTF-8",
                    "Origin": "https://lkfl.tatenergosbyt.ru",
                    "Referer": "https://lkfl.tatenergosbyt.ru/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36",
                    "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "YaBrowser";v="26.3", "Yowser";v="2.5"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                }

                # Формируем payload как в браузере
                indication = {"guid": guid, "value": str(value)}

                # Добавляем зону если есть
                if zone:
                    indication["zone"] = zone

                payload = {"domHoz": self.username, "indications": [indication]}

                _LOGGER.debug("Sending indication payload: %s", payload)

                response = await self.session.post(f"{self.base_url}/SetIndication", json=payload, headers=headers)

                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Set indication response: %s", data)

                    if data.get("success"):
                        # Проверяем результат для нашего GUID
                        for result in data.get("result", []):
                            if result.get("guid") == guid:
                                if result.get("result"):
                                    return {"success": True, "message": "Показания успешно отправлены", "data": data}
                                return {
                                    "success": False,
                                    "message": result.get("errorText", "Ошибка при отправке"),
                                    "data": data,
                                }

                        return {"success": False, "message": "GUID не найден в ответе", "data": data}
                    return {"success": False, "message": data.get("message", "Неизвестная ошибка"), "data": data}
                error_text = await response.text()
                _LOGGER.error("HTTP %s: %s", response.status, error_text)
                return {"success": False, "message": f"HTTP {response.status}", "error": error_text}

        except TimeoutError:
            _LOGGER.error("Timeout setting indication")
            return {"success": False, "message": "timeout"}
        except aiohttp.ClientError as err:
            _LOGGER.error("Client error setting indication: %s", err)
            return {"success": False, "message": str(err)}
        except Exception as err:
            _LOGGER.error("Unexpected error setting indication: %s", err)
            return {"success": False, "message": str(err)}

    def _get_unit_from_service(self, service_name: str) -> str:
        """Определить единицу измерения по названию услуги."""
        service_lower = service_name.lower()
        if "элект" in service_lower:
            return "кВт*ч"
        if "хвс" in service_lower or "вод" in service_lower or "гвс" in service_lower:
            return "куб.м"
        return "ед."
