# Transfer of water meter readings to Tatenergosbyt

[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/Gin-dev-code/hass-my-device)](LICENSE)

Интеграция для Home Assistant, позволяющая передавать показания счётчиков воды в личный кабинет "Татэнергосбыт".

## Возможности

- ✅ Передача текущих показаний воды
- ✅ Поддержка нескольких счётчиков (холодная/горячая вода)
- ✅ Настройка через UI — не требуется YAML
- ✅ Автоматическое обновление данных
- ✅ Поддержка HACS

## Установка

### Через HACS (рекомендуется)

1. Убедитесь, что [HACS](https://hacs.xyz/) установлен в Home Assistant
2. Нажмите на кнопку ниже, чтобы открыть репозиторий в HACS:

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=Gin-dev-code&repository=hass-my-device&category=Integration" target="_blank" rel="noreferrer noopener"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>

3. Нажмите **"Download"** и перезапустите Home Assistant

### Вручную

Скопируйте папку `custom_components/trans_met_read` в директорию `custom_components` вашего Home Assistant и перезапустите систему.

## Настройка

1. Перейдите в **Настройки → Устройства и сервисы → Добавить интеграцию**
2. Найдите **Transfer of water meter readings to Tatenergosbyt**
3. Введите ваши учётные данные от личного кабинета Татэнергосбыт:
   - Имя пользователя (логин)
   - Пароль
4. Нажмите **Submit**

После успешной настройки интеграция создаст сенсоры для каждого вашего счётчика воды.

## Платформы

| Платформа | Описание |
|-----------|----------|
| `sensor` | Показания счётчиков воды |
| `button` | Кнопка для ручной передачи показаний |

## Сервисы

### `trans_met_read.reload_data`

Принудительное обновление данных из API.

```yaml
service: trans_met_read.reload_data
