"""The LZString Base64 decompressor used by ManhuaGui.

This is a small, dependency-free Python implementation of the public
LZString decompression format: https://github.com/pieroxy/lz-string
"""

from __future__ import annotations

from collections.abc import Callable


_BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
_BASE64_INDEX = {char: index for index, char in enumerate(_BASE64_ALPHABET)}


class LZStringError(ValueError):
    pass


def decompress_from_base64(value: str) -> str:
    if value is None:
        return ""
    if value == "":
        return ""
    try:
        return _decompress(
            len(value),
            32,
            lambda index: _BASE64_INDEX[value[index]],
        )
    except (IndexError, KeyError) as exc:
        raise LZStringError("invalid LZString Base64 data") from exc


def _decompress(
    length: int,
    reset_value: int,
    get_next_value: Callable[[int], int],
) -> str:
    dictionary: list[str | None] = [None, None, None, None]
    enlarge_in = 4
    dictionary_size = 4
    number_bits = 3
    data_value = get_next_value(0)
    data_position = reset_value
    data_index = 1

    def read_bits(bit_count: int) -> int:
        nonlocal data_value, data_position, data_index
        bits = 0
        power = 1
        max_power = 1 << bit_count
        while power != max_power:
            result_bit = data_value & data_position
            data_position >>= 1
            if data_position == 0:
                data_position = reset_value
                if data_index >= length:
                    raise LZStringError("truncated LZString data")
                data_value = get_next_value(data_index)
                data_index += 1
            if result_bit:
                bits |= power
            power <<= 1
        return bits

    initial = read_bits(2)
    if initial == 0:
        char = chr(read_bits(8))
    elif initial == 1:
        char = chr(read_bits(16))
    elif initial == 2:
        return ""
    else:
        raise LZStringError("invalid initial LZString code")

    dictionary[3] = char
    current = char
    result = [char]

    while True:
        if data_index > length:
            raise LZStringError("unterminated LZString data")

        code = read_bits(number_bits)
        if code == 0:
            dictionary.append(chr(read_bits(8)))
            code = dictionary_size
            dictionary_size += 1
            enlarge_in -= 1
        elif code == 1:
            dictionary.append(chr(read_bits(16)))
            code = dictionary_size
            dictionary_size += 1
            enlarge_in -= 1
        elif code == 2:
            return "".join(result)

        if enlarge_in == 0:
            enlarge_in = 1 << number_bits
            number_bits += 1

        if code < len(dictionary) and dictionary[code] is not None:
            entry = dictionary[code]
        elif code == dictionary_size:
            entry = current + current[0]
        else:
            raise LZStringError(f"invalid LZString dictionary code: {code}")

        result.append(entry)
        dictionary.append(current + entry[0])
        dictionary_size += 1
        enlarge_in -= 1
        current = entry

        if enlarge_in == 0:
            enlarge_in = 1 << number_bits
            number_bits += 1

