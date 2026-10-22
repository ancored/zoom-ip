# zoom-ip

IP-диапазоны Zoom из официального списка Zoom в формате rule-set sing-box (`.srs`, `.json`) и текстом
(`.txt`). Собираются раз в сутки.

Зачем: медиа Zoom (звук, видео, демонстрация экрана) идёт по UDP 8801–8810 прямо на IP-адреса
медиасерверов. Доменов в этих пакетах нет, поэтому доменный набор вроде `geosite-zoom` их не ловит,
а адреса серверов клиент получает от Zoom, а не из DNS. Направить такой трафик можно только по IP.

## Файлы

| Файл | Что внутри |
|---|---|
| `zoom-ip.srs` / `.json` / `.txt` | подсети Zoom (`ip_cidr`) |
| `CHANGES.md` | что изменилось с прошлой сборки (он же — описание релиза) |

Ссылки:

```text
https://github.com/ancored/zoom-ip/releases/latest/download/zoom-ip.srs
https://raw.githubusercontent.com/ancored/zoom-ip/release/zoom-ip.srs
https://cdn.jsdelivr.net/gh/ancored/zoom-ip@release/zoom-ip.srs
```

Rule-set собирается в версии 2 и читается sing-box 1.10 и новее. Релиз выходит только при изменении
списка; хранятся последние 14 релизов, история изменений — в ветке `release`.

## sing-box

```json
{
  "route": {
    "rule_set": [
      {
        "type": "remote",
        "tag": "zoom-ip",
        "format": "binary",
        "url": "https://github.com/ancored/zoom-ip/releases/latest/download/zoom-ip.srs"
      }
    ],
    "rules": [
      {
        "network": "udp",
        "port_range": ["8801:8810"],
        "rule_set": "zoom-ip",
        "outbound": "direct"
      }
    ]
  }
}
```

Условия одного правила складываются: под него попадает только UDP на порты медиа Zoom и на адреса Zoom.
Для всего трафика Zoom уберите `network` и `port_range`; веб-клиент и API лучше направлять доменным
набором, он точнее.

## Как собирается

Источники — `Zoom.txt` и `ZoomMeetings.txt` с `assets.zoom.us/docs/ipranges/`, их публикует Zoom.
Подсети объединяются, пересекающиеся и соседние сливаются.

**Защита от сбоев.** Сборка падает и ничего не публикует, если источник недоступен, пуст или в нём есть
строка, которая не является подсетью (например, страница ошибки вместо списка), а также частный адрес
или слишком широкая подсеть (короче /8 для IPv4 и /16 для IPv6). Если итог потерял больше половины
подсетей, сборка тоже не публикуется. Последний удачный релиз при этом остаётся на месте.

## Локальный запуск

Нужен Python 3.9+ без сторонних пакетов; `.srs` собирает `sing-box rule-set compile`.

```sh
python3 -m unittest discover -s tests
python3 build.py --out out
sing-box rule-set compile --output out/zoom-ip.srs out/zoom-ip.json
```

## Лицензия

Код — [MIT](LICENSE). Данные — список Zoom Video Communications.
