"""Adapted from cmiedema25-rgb/freight-audit, MIT license.
Copyright (c) 2026 Charles Miedema.
Original source: https://github.com/cmiedema25-rgb/freight-audit/blob/f46a98d11ce559b0ecb483f256d8efeb3163a0f6/src/freight_audit/money.py
See third_party/LICENSE.cmiedema25-freight-audit.txt for full MIT terms.
Only the original rounded_minutes function is redistributed.
"""


def rounded_minutes(minutes: int, increment: int, mode: str):
    if minutes <= 0 or increment <= 0:
        return 0
    if mode == "CEILING_TO_INCREMENT":
        units = (minutes + increment - 1) // increment
    elif mode == "FLOOR_TO_INCREMENT":
        units = minutes // increment
    elif mode == "HALF_UP_TO_INCREMENT":
        units = (2 * minutes + increment) // (2 * increment)
    else:
        return None
    return units * increment
