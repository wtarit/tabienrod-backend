VEHICLE_TYPE_MAP = {
    'รย.1': set('กขจฉชฌญฎฐธพภวศษส'),
    'รย.2': set('นฬอฮ'),
    'รย.3': set('ฒณตถบผยรล'),
}

VALID_VEHICLE_TYPES = set(VEHICLE_TYPE_MAP.keys())


def letter_series_to_vehicle_type(letter_series: str) -> str | None:
    if not letter_series:
        return None
    first_char = letter_series[0]
    for vtype, chars in VEHICLE_TYPE_MAP.items():
        if first_char in chars:
            return vtype
    return None
