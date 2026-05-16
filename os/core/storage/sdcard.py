try:
    import machine
except:
    machine = None

try:
    import uos as os_lib
except:
    import os as os_lib

try:
    from micropython import const
except:
    def const(value):
        return value

import time


BOOT_SD_CONFIG = {
    "slot": 0,
    "baudrate": 1000000,
    "path": "/sd",
    "sck": 18,
    "mosi": 19,
    "miso": 16,
    "cs": 17
}

_MOUNT_STATE = {
    "mounted": False,
    "path": None,
    "card": None
}

_CMD_TIMEOUT = const(100)
_R1_IDLE_STATE = const(1 << 0)
_R1_ILLEGAL_COMMAND = const(1 << 2)
_TOKEN_CMD25 = const(0xFC)
_TOKEN_STOP_TRAN = const(0xFD)
_TOKEN_DATA = const(0xFE)


def _log(ctx, message, level="INFO"):
    if ctx is not None and hasattr(ctx, "log"):
        ctx.log(message, level)


def _crc7(buf, n):
    crc = 0
    for i in range(n):
        crc ^= buf[i]
        for j in range(8):
            crc = ((crc << 1) ^ (0x12 * (crc >> 7))) & 0xFF
    return crc


def to_int(value, default=None):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except:
        pass
    try:
        return int(str(value), 0)
    except:
        return default


def normalize_pin(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip().upper()
        if text.startswith("GP"):
            return to_int(text[2:], None)
        return to_int(text, None)
    return to_int(value, None)


def normalize_mount_path(path):
    if not isinstance(path, str) or not path:
        return "/sd"
    if path.startswith("/"):
        return path
    return "/" + path


def dir_exists(path):
    try:
        os_lib.listdir(path)
        return True
    except:
        return False


def is_accessible(path="/sd"):
    target = normalize_mount_path(path)
    return dir_exists(target) or dir_exists(target[1:])


def get_boot_sd_config(config=None):
    settings = {}
    for key in BOOT_SD_CONFIG:
        settings[key] = BOOT_SD_CONFIG[key]

    if isinstance(config, dict):
        storage = config.get("storage", {})
        if isinstance(storage, dict):
            sd = storage.get("sd", {})
            if isinstance(sd, dict):
                for key in settings:
                    if key in sd:
                        settings[key] = sd[key]

    settings["path"] = normalize_mount_path(settings.get("path"))
    return settings


class SDCard:
    def __init__(self, spi, cs, baudrate=1320000):
        self.spi = spi
        self.cs = cs
        self.cmdbuf = bytearray(6)
        self.dummybuf = bytearray(512)
        self.tokenbuf = bytearray(1)

        for i in range(512):
            self.dummybuf[i] = 0xFF

        self.dummybuf_memoryview = memoryview(self.dummybuf)
        self.init_card(baudrate)

    def init_spi(self, baudrate):
        try:
            master = self.spi.MASTER
        except AttributeError:
            self.spi.init(baudrate=baudrate, phase=0, polarity=0)
        else:
            self.spi.init(master, baudrate=baudrate, phase=0, polarity=0)

    def init_card(self, baudrate):
        self.cs.init(self.cs.OUT, value=1)
        self.init_spi(100000)

        for _ in range(16):
            self.spi.write(b"\xff")

        for _ in range(5):
            if self.cmd(0, 0) == _R1_IDLE_STATE:
                break
        else:
            raise OSError("no SD card")

        response = self.cmd(8, 0x01AA, 4)
        if response == _R1_IDLE_STATE:
            self.init_card_v2()
        elif response == (_R1_IDLE_STATE | _R1_ILLEGAL_COMMAND):
            self.init_card_v1()
        else:
            raise OSError("couldn't determine SD card version")

        if self.cmd(9, 0, 0, False) != 0:
            raise OSError("no response from SD card")

        csd = bytearray(16)
        self.readinto(csd)
        if csd[0] & 0xC0 == 0x40:
            self.sectors = ((csd[7] << 16 | csd[8] << 8 | csd[9]) + 1) * 1024
        elif csd[0] & 0xC0 == 0x00:
            c_size = (csd[6] & 0b11) << 10 | csd[7] << 2 | csd[8] >> 6
            c_size_mult = (csd[9] & 0b11) << 1 | csd[10] >> 7
            read_bl_len = csd[5] & 0b1111
            capacity = (c_size + 1) * (2 ** (c_size_mult + 2)) * (2 ** read_bl_len)
            self.sectors = capacity // 512
        else:
            raise OSError("SD card CSD format not supported")

        if self.cmd(16, 512) != 0:
            raise OSError("can't set 512 block size")

        self.init_spi(baudrate)

    def init_card_v1(self):
        for _ in range(_CMD_TIMEOUT):
            time.sleep_ms(50)
            self.cmd(55, 0)
            if self.cmd(41, 0) == 0:
                self.cdv = 512
                return
        raise OSError("timeout waiting for v1 card")

    def init_card_v2(self):
        for _ in range(_CMD_TIMEOUT):
            time.sleep_ms(50)
            self.cmd(58, 0, 4)
            self.cmd(55, 0)
            if self.cmd(41, 0x40000000) == 0:
                self.cmd(58, 0, -4)
                ocr = self.tokenbuf[0]
                if not ocr & 0x40:
                    self.cdv = 512
                else:
                    self.cdv = 1
                return
        raise OSError("timeout waiting for v2 card")

    def cmd(self, cmd, arg, final=0, release=True, skip1=False):
        self.cs(0)
        buf = self.cmdbuf
        buf[0] = 0x40 | cmd
        buf[1] = arg >> 24
        buf[2] = arg >> 16
        buf[3] = arg >> 8
        buf[4] = arg
        buf[5] = _crc7(buf, 5) | 0x01
        self.spi.write(buf)

        if skip1:
            self.spi.readinto(self.tokenbuf, 0xFF)

        for _ in range(_CMD_TIMEOUT):
            self.spi.readinto(self.tokenbuf, 0xFF)
            response = self.tokenbuf[0]
            if not (response & 0x80):
                if final < 0:
                    self.spi.readinto(self.tokenbuf, 0xFF)
                    final = -1 - final
                for _ in range(final):
                    self.spi.write(b"\xff")
                if release:
                    self.cs(1)
                    self.spi.write(b"\xff")
                return response

        self.cs(1)
        self.spi.write(b"\xff")
        return -1

    def readinto(self, buf):
        self.cs(0)

        for _ in range(_CMD_TIMEOUT):
            self.spi.readinto(self.tokenbuf, 0xFF)
            if self.tokenbuf[0] == _TOKEN_DATA:
                break
            time.sleep_ms(1)
        else:
            self.cs(1)
            raise OSError("timeout waiting for response")

        mv = self.dummybuf_memoryview
        if len(buf) != len(mv):
            mv = mv[:len(buf)]
        self.spi.write_readinto(mv, buf)
        self.spi.write(b"\xff")
        self.spi.write(b"\xff")
        self.cs(1)
        self.spi.write(b"\xff")

    def write(self, token, buf):
        self.cs(0)
        self.spi.read(1, token)
        self.spi.write(buf)
        self.spi.write(b"\xff")
        self.spi.write(b"\xff")

        if (self.spi.read(1, 0xFF)[0] & 0x1F) != 0x05:
            self.cs(1)
            self.spi.write(b"\xff")
            return

        while self.spi.read(1, 0xFF)[0] == 0:
            pass

        self.cs(1)
        self.spi.write(b"\xff")

    def write_token(self, token):
        self.cs(0)
        self.spi.read(1, token)
        self.spi.write(b"\xff")
        while self.spi.read(1, 0xFF)[0] == 0x00:
            pass
        self.cs(1)
        self.spi.write(b"\xff")

    def readblocks(self, block_num, buf):
        self.spi.write(b"\xff")
        nblocks = len(buf) // 512
        assert nblocks and not len(buf) % 512, "Buffer length is invalid"

        if nblocks == 1:
            if self.cmd(17, block_num * self.cdv, release=False) != 0:
                self.cs(1)
                raise OSError(5)
            self.readinto(buf)
            return

        if self.cmd(18, block_num * self.cdv, release=False) != 0:
            self.cs(1)
            raise OSError(5)

        offset = 0
        mv = memoryview(buf)
        while nblocks:
            self.readinto(mv[offset:offset + 512])
            offset += 512
            nblocks -= 1
        if self.cmd(12, 0, skip1=True):
            raise OSError(5)

    def writeblocks(self, block_num, buf):
        self.spi.write(b"\xff")
        nblocks, err = divmod(len(buf), 512)
        assert nblocks and not err, "Buffer length is invalid"

        if nblocks == 1:
            if self.cmd(24, block_num * self.cdv) != 0:
                raise OSError(5)
            self.write(_TOKEN_DATA, buf)
            return

        if self.cmd(25, block_num * self.cdv) != 0:
            raise OSError(5)

        offset = 0
        mv = memoryview(buf)
        while nblocks:
            self.write(_TOKEN_CMD25, mv[offset:offset + 512])
            offset += 512
            nblocks -= 1
        self.write_token(_TOKEN_STOP_TRAN)

    def ioctl(self, op, arg):
        if op == 4:
            return self.sectors
        if op == 5:
            return 512


def mount_boot_sd(ctx=None, config=None):
    settings = get_boot_sd_config(config)
    target = settings.get("path", "/sd")

    if is_accessible(target):
        _MOUNT_STATE["mounted"] = True
        _MOUNT_STATE["path"] = target
        return target

    if machine is None:
        _log(ctx, "SD bootstrap unavailable", "WARN")
        return None

    sck_pin = normalize_pin(settings.get("sck"))
    mosi_pin = normalize_pin(settings.get("mosi"))
    miso_pin = normalize_pin(settings.get("miso"))
    cs_pin = normalize_pin(settings.get("cs"))

    if None in (sck_pin, mosi_pin, miso_pin, cs_pin):
        _log(ctx, "Missing SD bootstrap pins", "ERROR")
        return None

    try:
        spi = machine.SPI(
            int(settings.get("slot", 0)),
            baudrate=to_int(settings.get("baudrate"), 1000000),
            polarity=0,
            phase=0,
            sck=machine.Pin(sck_pin),
            mosi=machine.Pin(mosi_pin),
            miso=machine.Pin(miso_pin)
        )
        card = SDCard(spi, machine.Pin(cs_pin, machine.Pin.OUT))
        vfs = os_lib.VfsFat(card)
        os_lib.mount(vfs, target)
        _MOUNT_STATE["mounted"] = True
        _MOUNT_STATE["path"] = target
        _MOUNT_STATE["card"] = card
        _log(ctx, "Mounted SD card at %s" % target)
        return target
    except Exception as e:
        _log(ctx, "SD bootstrap mount failed: %s" % e, "ERROR")
        return None
