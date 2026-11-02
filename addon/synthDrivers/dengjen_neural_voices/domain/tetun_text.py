# -*- coding: UTF-8 -*-
"""Text normalisation for Tetun, applied before the text reaches espeak-ng and the voice.

espeak-ng reads plain numbers well (see docs/PHONEMES.md in the tetun-tts repo) but cannot do the Tetun forms of times, dates,
decimals and large amounts, which need the words rearranged. The forms below were given by a Tetun language expert (2026-10-22):
  17:00        -> tuku 17                       (minutes of 00 are left out)
  10:30        -> tuku 10 liu minutu 30
  17/03/2022   -> loron 17, fulan Marsu, tinan 2022
  1,35         -> 1, virgula 35                 (the decimals are read as a number: ida virgula tolunulu resin lima)
  $1,35 biliaun -> dolar biliaun 1, virgula 35    (the scale word comes before the number)
  5mm          -> milímetru 5                   (units are written after the number but read before it; expert, 2026-10-27)
  Dr. Silva    -> doutór Silva                  (titles and a few abbreviations are read in full)
Only digits and a few words are produced; espeak-ng reads the numbers.
"""
import re

_SCALE = r"(?:mili|bili|trili)a?un|(?:mi|bi|tri)lhaun"
_SCALE_FIX = {"milhaun": "miliaun", "bilhaun": "biliaun", "trilhaun": "triliaun"}

_AMOUNT_SCALE = re.compile(
    r"(?P<cur>US\s?\$\s?|\$\s?)?(?P<num>\d+(?:[.,]\d+)?)\s+(?P<scale>" + _SCALE + r")\b", re.IGNORECASE
)
_DATE = re.compile(r"(?:\bloron\s+)?(?<![\d./-])(\d{1,2})([/.-])(\d{1,2})\2(\d{4})(?![\d/-])(?!\.\d)", re.IGNORECASE)
_TIME = re.compile(r"(?:(?P<tuku>\btuku)\s+)?(?<![\d:])(?P<h>[01]?\d|2[0-3])(?::|h)(?P<m>[0-5]\d)(?![\d:])", re.IGNORECASE)
# Units: the written form (case matters: GB is gigabait, but gb is not) and the Tetun word read before the number.
_UNITS = {"mm": "milímetru", "cm": "sentímetru", "km": "kilómetru", "m": "metru", "kg": "kilograma", "mg": "miligrama", "g": "grama",
          "ml": "mililitru", "l": "litru", "t": "tonelada", "ton": "tonelada", "GB": "gigabait", "MB": "megabait", "KB": "kilobait",
          "GHz": "gigahertz", "Hz": "hertz"}
_UNIT = re.compile(r"(?<![\w.,])(?P<num>\d+(?:[.,]\d+)?)\s?(?P<unit>" + "|".join(sorted(_UNITS, key=len, reverse=True)) + r")\b(?![.,]?\d)")
_WORDS = (
    (re.compile(r"\bno\s+sst\b\.?", re.IGNORECASE), "ho selu-seluk tan"),
    (re.compile(r"\bsst\.", re.IGNORECASE), "ho selu-seluk tan"),
    (re.compile(r"\bDra\.(?=\s)"), "doutóra"),
    (re.compile(r"\bDr\.(?=\s)"), "doutór"),
    (re.compile(r"\bSra\.(?=\s)"), "senhora"),
    (re.compile(r"\bSr\.(?=\s)"), "senhór"),
    (re.compile(r"\b(?:no|nu)\.(?=\s?\d)", re.IGNORECASE), "númeru"),
)
_DECIMAL = re.compile(r"(?<![\d.,])(\d+),(\d{1,2})(?![\d])")


def _scale(m):
    scale = _SCALE_FIX.get(m.group("scale").lower(), m.group("scale").lower())
    return ("dolar " if m.group("cur") else "") + scale + " " + m.group("num")


_MONTHS = ("Janeiru", "Fevereiru", "Marsu", "Abríl", "Maiu", "Junhu", "Julhu", "Agostu", "Setembru", "Outubru", "Novembru", "Dezembru")


def _date(m):
    day, month, year = int(m.group(1)), int(m.group(3)), m.group(4)
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return m.group(0)
    return f"loron {day}, fulan {_MONTHS[month - 1]}, tinan {year}"


def _time(m):
    hours, minutes = int(m.group("h")), int(m.group("m"))
    out = f"tuku {hours}" + (f" liu minutu {minutes}" if minutes else "")
    return out


def _decimal(m):
    decimals = m.group(2)
    zeros = " ".join("0" for _ in range(len(decimals) - len(decimals.lstrip("0"))))
    rest = decimals.lstrip("0")
    parts = [m.group(1) + ",", "virgula"] + ([zeros] if zeros else []) + ([rest] if rest else [])  # the comma gives the pause before "virgula" the expert asked for
    return " ".join(parts)


def normalise(text: str) -> str:
    for pattern, word in _WORDS:
        text = pattern.sub(word, text)
    text = _UNIT.sub(lambda m: _UNITS[m.group("unit")] + " " + m.group("num"), text)
    text = _AMOUNT_SCALE.sub(_scale, text)
    text = _DATE.sub(_date, text)
    text = _TIME.sub(_time, text)
    text = _DECIMAL.sub(_decimal, text)
    return text
