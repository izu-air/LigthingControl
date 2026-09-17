# LigthingControl

Управляет лампочкой Яндекса и BLE RGB-лентой из одного места. Есть режим ambilight —
подсветка подстраивается под цвет экрана.

## Установка

Нужен Python 3.10+ (python.org, при установке отметь "Add python.exe to PATH") и
Bluetooth-адаптер на компьютере.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config.example.yaml config.yaml
```

## Настройка

Открой `config.yaml` и заполни:

**Яндекс** — `oauth_token` и `device_id`. Токен получается через свой OAuth-клиент на
oauth.yandex.ru с доступом к "умному дому". device_id смотри в ответе:

```powershell
Invoke-RestMethod -Uri "https://api.iot.yandex.net/v1.0/user/info" -Headers @{Authorization="Bearer ТОКЕН"} | ConvertTo-Json -Depth 10
```

(бери id из раздела `devices`, не из `scenarios`).

**Лента** — `mac_address` и `protocol`. MAC найдёшь так:

```powershell
python scan_ble.py
```

Протокол определяется по характеристикам устройства:

```powershell
python list_ble_services.py <MAC>
```

Если видишь характеристику `0000ffd9-...` — `protocol: triones`. Если `0000fff3-...` —
`protocol: happy_lighting`. Если ни то, ни другое не подошло, попробуй разные байты вручную:

```powershell
python send_raw.py <MAC> <UUID> "7E 00 05 03 FF 00 00 00 EF"
```

и добавь рабочий вариант в словарь `PROTOCOLS` в `unified_lighting/devices/rgb_strip_ble.py`.

## Запуск

Проще всего через окно:

```powershell
python app.py
```

Ярлык на рабочий стол:

```powershell
powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
```

Или через консоль:

```powershell
python -m unified_lighting power on
python -m unified_lighting set-color 255 80 0
python -m unified_lighting ambilight
```

## На заметку

- Лампочки "совместимые с Яндексом" часто на самом деле подключены через облако Tuya и не
  выдерживают частых обновлений — поэтому во время ambilight лампочка обновляется раз в
  1.5 секунды, а лента — на полной скорости.
- Цветовая модель лампочки (rgb/hsv) определяется автоматически.
- Тесты: `pytest`.
