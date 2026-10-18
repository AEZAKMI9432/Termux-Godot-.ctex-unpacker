#!/usr/bin/env python3
"""Godot cmd .ctex texture unpacker
Create by Aeza Lab.

Интерактивное извлечение PNG/WebP из .ctex/.stex Godot.

Скрипт ищет контейнеры .ctex/.stex в своей собственной папке
(включая подпапки), показывает нумерованный список и по выбранному
режиму распаковывает файлы рядом с исходниками.

Режимы:
  <номер>, несколько через запятую  — распаковать выбранные
  all                               — распаковать все
  zip                               — unpack all in .zip (все в один архив)
  reset                             — перезапустить программу
  exit                              — выйти

Запуск: python extract_ctex.py
"""
from __future__ import annotations

import os
import struct
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEXTURE_EXTS = (".ctex", ".stex")

PNG_SIG = b"\x89PNG\r\n\x1a\n"
IEND = b"IEND"

try:
    import zlib  # noqa: F401
    ZIP_METHOD = zipfile.ZIP_DEFLATED
except ImportError:
    ZIP_METHOD = zipfile.ZIP_STORED

BANNER = """Godot cmd .ctex texture unpacker
Create by Aeza Lab."""

def find_png(data: bytes, pos: int = 0) -> tuple[int, int] | None:
    """Границы (start, end) первого полного PNG в data начиная с pos."""
    start = data.find(PNG_SIG, pos)
    if start == -1:
        return None
    iend = data.find(IEND, start)
    if iend == -1:
        return None
    return start, iend + len(IEND) + 4  # после IEND: 4 байта длины + 4 CRC

def extract_webp(data: bytes) -> bytes | None:
    idx = data.find(b"WEBP")
    if idx == -1:
        return None
    riff_start = idx - 8  # "RIFF" + размер стоят перед "WEBP"
    if riff_start < 0 or data[riff_start:riff_start + 4] != b"RIFF":
        return None
    size = struct.unpack_from("<I", data, riff_start + 4)[0] + 8
    return data[riff_start:riff_start + size]

def extract_texture(data: bytes) -> tuple[bytes, str] | None:
    """Первое (полное) изображение: PNG (lossless) или WebP (lossy)."""
    found = find_png(data)
    if found:
        start, end = found
        return data[start:end], ".png"
    webp = extract_webp(data)
    if webp:
        return webp, ".webp"
    return None

def scan_textures() -> list[Path]:
    files = [
        p for p in SCRIPT_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in TEXTURE_EXTS
    ]
    return sorted(files, key=lambda p: str(p).lower())

def human_size(num: float) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if num < 1024:
            return f"{num:.0f} {unit}" if unit == "Б" else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} ТБ"

def result_name(rel_path: Path, ext: str) -> Path:
    """Относительное имя результата: 'icon.png-48da...ctex' -> 'icon.png'
    (PNG) или 'icon.webp' (WebP).

    Дефис режем только последний: имена вида 'my-icon.png-<md5>.ctex'
    не ломаются.
    """
    stem = rel_path.stem              # 'icon.png-48da...ctex' -> 'icon.png-48da...'
    base = stem.rsplit("-", 1)[0]     # -> 'icon.png'
    dot = base.rfind(".")
    if dot == -1:
        return Path(base + ext)
    return Path(base[:dot] + ext)

def unique_path(dest: Path) -> Path:
    """Если файл с таким именем уже есть — добавляет _2, _3, ..."""
    if not dest.exists():
        return dest
    for i in range(2, 1000):
        candidate = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
        if not candidate.exists():
            return candidate
    return dest

def unpack(tex: Path) -> bool:
    try:
        data = tex.read_bytes()
    except OSError as exc:
        print(f"!!  {tex.name}: не читается ({exc})")
        return False

    tex_data = extract_texture(data)
    if tex_data is None:
        print(f"--  {tex.name}: нет PNG/WebP внутри (вероятно VRAM-сжатие)")
        return False

    content, ext = tex_data
    dest = unique_path(tex.parent / result_name(tex, ext))
    try:
        dest.write_bytes(content)
    except OSError as exc:
        print(f"!!  {dest.name}: не записывается ({exc})")
        return False

    print(f"OK  {tex.name} -> {dest.name}")
    return True

def pack_all_to_zip(files: list[Path]) -> None:
    """Распаковывает все контейнеры и складывает результаты в один zip."""
    archive = unique_path(SCRIPT_DIR / "unpacked_textures.zip")
    used_names: set[str] = set()
    extracted = 0
    skipped = 0

    try:
        zf = zipfile.ZipFile(archive, "w", ZIP_METHOD)
    except OSError as exc:
        print(f"!!  не создать архив {archive.name}: {exc}")
        return

    with zf:
        for tex in files:
            try:
                data = tex.read_bytes()
            except OSError as exc:
                print(f"!!  {tex.name}: не читается ({exc})")
                skipped += 1
                continue

            tex_data = extract_texture(data)
            if tex_data is None:
                print(f"--  {tex.name}: нет PNG/WebP внутри (вероятно VRAM-сжатие)")
                skipped += 1
                continue

            content, ext = tex_data
            rel = tex.relative_to(SCRIPT_DIR)
            arc = result_name(rel, ext)
            if str(rel.parent) != ".":
                arc = rel.parent / arc

            base_arc = arc
            i = 2
            while str(arc) in used_names:
                arc = base_arc.with_name(f"{base_arc.stem}_{i}{base_arc.suffix}")
                i += 1
            used_names.add(str(arc))

            try:
                zf.writestr(str(arc), content)
            except OSError as exc:
                print(f"!!  {tex.name}: не упаковывается ({exc})")
                skipped += 1
                continue

            extracted += 1
            print(f"OK  {tex.name} -> {arc}")

    print(f"\nАрхив готов: {archive}")
    print(f"Упаковано: {extracted}, пропущено: {skipped}")

def reset_program() -> None:
    """Чистый перезапуск процесса с тем же скриптом."""
    print("Перезапуск...\n")
    try:
        os.execv(sys.executable, [sys.executable, os.path.abspath(sys.argv[0])])
    except OSError as exc:
        print(f"!!  не удалось перезапуститься ({exc}) — запусти скрипт заново")

def print_list(files: list[Path]) -> None:
    print(f"\nПапка: {SCRIPT_DIR}")
    print(f"Найдено контейнеров: {len(files)}\n")
    for i, p in enumerate(files, 1):
        rel = p.relative_to(SCRIPT_DIR)
        print(f"  {i:>3}) {rel}  [{human_size(p.stat().st_size)}]")
    print()

def print_help() -> None:
    print("Команды:")
    print("  <номер>      распаковать файл по номеру (несколько — через запятую)")
    print("  all          распаковать все найденные контейнеры")
    print("  zip          unpack all in .zip — распаковать все в unpacked_textures.zip")
    print("  reset        перезапустить программу")
    print("  exit         выйти")

def main() -> None:
    print(BANNER)
    while True:
        files = scan_textures()
        if not files:
            print(f"В папке {SCRIPT_DIR} нет файлов .ctex/.stex")
            return

        print_list(files)
        print_help()
        raw = input("\nВыбор: ").strip().lower()

        if raw in ("exit", "q", "й", "quit"):
            print(f"Рабочая папка скрипта: {SCRIPT_DIR}")
            return

        if raw in ("reset", "r", "рестарт", "перезапуск"):
            reset_program()
            return  # сюда попадём только если execv не сработал

        if raw in ("zip", "архив", "unpack all in .zip"):
            pack_all_to_zip(files)
            continue

        if raw in ("all", "a", "все", "всё"):
            for tex in files:
                unpack(tex)
            continue

        try:
            indexes = [int(part) for part in raw.replace(",", " ").split()]
        except ValueError:
            print("Не понял ввод: номер из списка, 'all', 'zip', 'reset' или 'exit'")
            continue

        for idx in indexes:
            if 1 <= idx <= len(files):
                unpack(files[idx - 1])
            else:
                print(f"Нет файла с номером {idx}")

if __name__ == "__main__":
    main()