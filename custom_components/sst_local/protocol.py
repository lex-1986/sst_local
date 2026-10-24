"""Local TCP protocol of SST / Teploluxe thermostats (port 6350).

Frame: 0x02 'T' <dir> <cmd> <len u16 BE> <payload> <CRC16 BE>
  dir 'Q' - request from the client, 'A' - answer from the device.
  cmd 'R' - read configuration, 'W' - write.
  In answers to 'W' the cmd byte is a status code: 0 = OK.
CRC: CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over the whole frame.
Payload: sequence of TLV blocks <tag char> <len u16 BE> <value>.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import struct

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 6350
TIMEOUT = 5
RETRY_DELAY = 1

MODE_MANUAL = 0
MODE_CHART = 1
MODE_VACATION = 2

DAYS = 7
POINTS_PER_DAY = 4
CHART_POINTS = DAYS * POINTS_PER_DAY
MIN_CHART_TEMP = 0
MAX_CHART_TEMP = 45


class SSTError(Exception):
    """Communication error."""


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def build_frame(cmd: str, payload: bytes = b"") -> bytes:
    frame = b"\x02TQ" + cmd.encode() + struct.pack(">H", len(payload)) + payload
    return frame + struct.pack(">H", crc16(frame))


def parse_tlv(payload: bytes) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    i = 0
    while i + 3 <= len(payload):
        tag = chr(payload[i])
        length = int.from_bytes(payload[i + 1:i + 3], "big")
        result[tag] = payload[i + 3:i + 3 + length]
        i += 3 + length
    return result


def _signed(value: int) -> int:
    return value - 256 if value > 127 else value


@dataclass
class ThermostatState:
    """Decoded answer to the 'R' command (MCS350)."""

    raw: dict[str, bytes] = field(repr=False)
    status: bool
    mode: int
    sensor_bits: int
    temp_manual: int
    temp_vacation: int
    temp_air_limit: int
    temp_air_correction: int
    temp_floor: int | None
    temp_air: int | None
    day_of_week: int
    event: int
    chart: list[tuple[int, int]]
    heating: bool
    relay_minutes: int | None
    wifi_level: int | None
    device_type: str
    firmware: str
    mac: str
    open_window_minutes: int

    @property
    def floor_sensor_error(self) -> bool:
        return self.temp_floor is None

    @property
    def uses_floor_sensor(self) -> bool:
        return bool(self.sensor_bits & 0x02)

    @property
    def uses_air_sensor(self) -> bool:
        return bool(self.sensor_bits & 0x01)

    @property
    def chart_temperature(self) -> int | None:
        index = self.day_of_week * 4 + self.event
        if 0 <= index < len(self.chart):
            return self.chart[index][1]
        return None

    @property
    def target_temperature(self) -> int | None:
        if self.mode == MODE_MANUAL:
            return self.temp_manual
        if self.mode == MODE_VACATION:
            return self.temp_vacation
        return self.chart_temperature

    def settings_bytes(self) -> bytearray:
        return bytearray(self.raw["S"][:7])


def parse_state(frame: bytes) -> ThermostatState:
    if len(frame) < 8 or frame[:3] != b"\x02TA":
        raise SSTError(f"Неожиданный ответ: {frame.hex(' ')}")
    if crc16(frame[:-2]) != int.from_bytes(frame[-2:], "big"):
        raise SSTError("Ошибка CRC в ответе")
    if frame[3] != ord("R"):
        raise SSTError(f"Устройство вернуло ошибку {frame[3]:#04x}")
    length = int.from_bytes(frame[4:6], "big")
    tlv = parse_tlv(frame[6:6 + length])
    if "S" not in tlv or "T" not in tlv:
        raise SSTError("В ответе нет блоков S/T")

    s = tlv["S"]
    t = tlv["T"]
    floor = _signed(t[0])
    chart_raw = tlv.get("C", b"")
    chart = [
        (int.from_bytes(chart_raw[i:i + 2], "big"), chart_raw[i + 2])
        for i in range(0, len(chart_raw) - 2, 3)
    ]
    relay = tlv.get("L")
    relay_minutes = None
    if relay and len(relay) >= 2:
        relay_minutes = int.from_bytes(relay[0:2], "big") * 60 + (relay[2] if len(relay) > 2 else 0)
    ident = tlv.get("I", b"")

    return ThermostatState(
        raw=tlv,
        status=s[0] == 1,
        mode=s[1],
        sensor_bits=s[2],
        temp_manual=s[3],
        temp_vacation=s[4],
        temp_air_limit=s[5],
        temp_air_correction=_signed(s[6]),
        temp_floor=None if floor == -127 else floor,
        temp_air=_signed(t[1]) if len(t) > 3 else None,
        day_of_week=t[-2],
        event=t[-1],
        chart=chart,
        heating=tlv.get("H", b"\x00")[0] == 1,
        relay_minutes=relay_minutes,
        wifi_level=tlv["W"][0] if "W" in tlv else None,
        device_type=ident[:2].decode(errors="replace"),
        firmware=".".join(chr(b) for b in ident[2:5]),
        mac=tlv.get("M", b"").decode(errors="replace"),
        open_window_minutes=tlv.get("O", b"\x00")[0],
    )


class SSTThermostatClient:
    """One request per TCP connection, serialized by a lock."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._lock = asyncio.Lock()

    async def _request(self, frame: bytes) -> bytes:
        # Устройство обслуживает одно соединение за раз: при столкновении с другим
        # клиентом (приложение, второй опрос) повторяем один раз. Записи идемпотентны.
        try:
            return await self._request_once(frame)
        except SSTError as err:
            _LOGGER.debug("Повтор запроса к %s после ошибки: %s", self.host, err)
            await asyncio.sleep(RETRY_DELAY)
            return await self._request_once(frame)

    async def _request_once(self, frame: bytes) -> bytes:
        async with self._lock:
            try:
                async with asyncio.timeout(TIMEOUT):
                    reader, writer = await asyncio.open_connection(self.host, self.port)
                    try:
                        writer.write(frame)
                        await writer.drain()
                        header = await reader.readexactly(6)
                        length = int.from_bytes(header[4:6], "big")
                        rest = await reader.readexactly(length + 2)
                    finally:
                        writer.close()
                        try:
                            await writer.wait_closed()
                        except OSError:
                            pass
            except (OSError, asyncio.IncompleteReadError, TimeoutError) as err:
                raise SSTError(f"Нет связи с {self.host}:{self.port}: {err!r}") from err
        return header + rest

    async def read_state(self) -> ThermostatState:
        return parse_state(await self._request(build_frame("R")))

    async def write(self, payload: bytes) -> None:
        answer = await self._request(build_frame("W", payload))
        if crc16(answer[:-2]) != int.from_bytes(answer[-2:], "big"):
            raise SSTError("Ошибка CRC в ответе на запись")
        if answer[3] != 0:
            raise SSTError(f"Запись отклонена устройством, код {answer[3]:#04x}")

    async def write_settings(self, settings: bytes | bytearray) -> None:
        if len(settings) != 7:
            raise ValueError("Блок S должен быть 7 байт")
        await self.write(b"S\x00\x07" + bytes(settings))

    async def write_chart(self, chart: list[tuple[int, int]]) -> None:
        """Записать расписание целиком: 7 дней x 4 точки (минуты от полуночи, °C), пн = день 0."""
        await self.write(b"C" + struct.pack(">H", CHART_POINTS * 3) + encode_chart(chart))


def encode_chart(chart: list[tuple[int, int]]) -> bytes:
    if len(chart) != CHART_POINTS:
        raise ValueError(f"Расписание должно содержать {CHART_POINTS} точек")
    data = bytearray()
    for minutes, temperature in chart:
        if not 0 <= minutes <= 1440:
            raise ValueError(f"Неверное время точки расписания: {minutes} мин")
        if not MIN_CHART_TEMP <= temperature <= MAX_CHART_TEMP:
            raise ValueError(f"Неверная температура точки расписания: {temperature}")
        data += struct.pack(">HB", minutes, temperature)
    return bytes(data)
