#!/usr/bin/env python3
"""Сборка rule-set sing-box из официального списка IP-диапазонов Zoom."""
import argparse
import ipaddress
import json
import os
import sys
import urllib.request
from pathlib import Path

SOURCES = (
    "https://assets.zoom.us/docs/ipranges/Zoom.txt",
    "https://assets.zoom.us/docs/ipranges/ZoomMeetings.txt",
)
NAME = "zoom-ip"
MAX_BYTES = 1024 * 1024
# Итог, потерявший больше половины подсетей, не публикуется.
SHRINK_LIMIT = 0.5
MIN_PREFIX = {4: 8, 6: 16}
RULESET_VERSION = 2  # читается sing-box 1.10 и новее


def http_get(url):
    request = urllib.request.Request(url, headers={"User-Agent": NAME})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("источник больше 1 МиБ")
    return data.decode("utf-8")


def parse(text):
    """Строки списка → подсети; любая непонятная строка — ошибка, а не пропуск."""
    networks = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            network = ipaddress.ip_network(line, strict=False)
        except ValueError:
            raise ValueError(f"не подсеть: {line!r}") from None
        if network.prefixlen < MIN_PREFIX[network.version] or not network.is_global:
            raise ValueError(f"недопустимая подсеть: {line}")
        networks.append(network)
    if not networks:
        raise ValueError("пустой список")
    return networks


def merge(networks):
    return [str(network) for version in (4, 6)
            for network in ipaddress.collapse_addresses(n for n in networks if n.version == version)]


def changes_report(networks, old):
    new, old = set(networks), set(old or [])
    lines = [f"- {len(networks)} подсетей (+{len(new - old)} / −{len(old - new)})"]
    lines += [f"  - добавлена `{n}`" for n in sorted(new - old, key=ipaddress.ip_network)]
    lines += [f"  - убрана `{n}`" for n in sorted(old - new, key=ipaddress.ip_network)]
    lines += ["", "Источники:"] + [f"- {url}" for url in SOURCES]
    return "\n".join(lines) + "\n"


def build(texts, previous, out):
    """Собирает списки в out; возвращает True, если подсети изменились."""
    networks = merge([network for text in texts for network in parse(text)])
    old_file = previous / (NAME + ".txt") if previous else None
    old = old_file.read_text(encoding="utf-8").split() if old_file and old_file.is_file() else None
    if old and len(networks) < len(old) * SHRINK_LIMIT:
        raise SystemExit(f"итог сократился с {len(old)} до {len(networks)}, публикация отменена")
    out.mkdir(parents=True, exist_ok=True)
    (out / (NAME + ".txt")).write_text("".join(n + "\n" for n in networks), encoding="utf-8")
    ruleset = {"version": RULESET_VERSION, "rules": [{"ip_cidr": networks}]}
    (out / (NAME + ".json")).write_text(json.dumps(ruleset, indent=1) + "\n", encoding="utf-8")
    (out / "CHANGES.md").write_text(changes_report(networks, old), encoding="utf-8")
    return networks != old


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, help="папка прошлой сборки (ветка release)")
    parser.add_argument("--out", type=Path, default=Path("out"))
    args = parser.parse_args(argv)
    changed = build([http_get(url) for url in SOURCES], args.previous, args.out)
    print("изменения есть" if changed else "без изменений")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"changed={'true' if changed else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
