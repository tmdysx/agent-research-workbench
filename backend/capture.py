"""截图和录屏：借 Windows 自带的截图工具，截好的、录好的自己进随堂笔记的草稿。

作者 2026-09-27：「你能不能参考一下微信的截图或者windows自带的可以截图或者录屏功能的能力？」
- 不自己写框选：系统的截图工具能框一块、截窗口、录屏带声音，大家都用惯了
- 怎么叫它：替你按系统快捷键 `Win+Shift+S`（截图）/ `Win+Shift+R`（录屏）。
  以前的 `ms-screenclip:` 微软 2025-05 停用了；新的调用办法只有商店打包的软件才拿得到结果
- 截图从剪贴板拿：只拿「按下以后新来的图」，你原来复制的东西不当截图
- 录屏从截图工具自动保存的文件夹捡（默认 视频\\Screen Recordings）：出现新的视频、大小不再变，就复制一份（原件不动）
- 一次只等一件；能喊停
读剪贴板、按键、找文件夹都用 Windows 自己的接口（ctypes），不加新的库。
"""
from __future__ import annotations

import ctypes
import os
import struct
import sys
import threading
import time
import zlib
from pathlib import Path

IMAGE_WAIT = 90                            # 等你框选截图最多多少秒
VIDEO_WAIT = 2 * 3600                      # 等录屏最多多少秒
VIDEO_EXTS = (".mp4", ".webm", ".mov")
CF_DIB = 8
VK = {"ctrl": 0x11, "alt": 0x12, "shift": 0x10, "lwin": 0x5B, "rwin": 0x5C}


class Busy(Exception):
    pass


def available() -> bool:
    return sys.platform == "win32"


if available():
    from ctypes import wintypes
    _u, _k, _s = ctypes.windll.user32, ctypes.windll.kernel32, ctypes.windll.shell32
    _u.GetClipboardSequenceNumber.restype = wintypes.DWORD
    _u.OpenClipboard.argtypes = [wintypes.HWND]
    _u.OpenClipboard.restype = wintypes.BOOL
    _u.CloseClipboard.restype = wintypes.BOOL
    _u.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    _u.IsClipboardFormatAvailable.restype = wintypes.BOOL
    _u.GetClipboardData.argtypes = [wintypes.UINT]
    _u.GetClipboardData.restype = wintypes.HANDLE
    _u.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    _u.RegisterClipboardFormatW.restype = wintypes.UINT
    _u.GetAsyncKeyState.argtypes = [ctypes.c_int]
    _u.GetAsyncKeyState.restype = ctypes.c_short
    _k.GlobalLock.argtypes = [wintypes.HGLOBAL]
    _k.GlobalLock.restype = ctypes.c_void_p
    _k.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    _k.GlobalUnlock.restype = wintypes.BOOL
    _k.GlobalSize.argtypes = [wintypes.HGLOBAL]
    _k.GlobalSize.restype = ctypes.c_size_t

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class _MOUSEINPUT(ctypes.Structure):          # 只为把 INPUT 撑到系统要的大小
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class _INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]

    _u.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int]
    _u.SendInput.restype = wintypes.UINT

    class _GUID(ctypes.Structure):
        _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

    _s.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(_GUID), wintypes.DWORD, wintypes.HANDLE,
                                        ctypes.POINTER(ctypes.c_wchar_p)]
    _ole = ctypes.windll.ole32
    _ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]


# ---------------------------------------------------------------- 图片格式

def png(w: int, h: int, raw: bytes) -> bytes:
    """raw = 每行前面一个 0 字节 + 这一行的 RGB。"""
    def chunk(t: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def dib_to_png(d: bytes) -> bytes:
    """剪贴板里的 BMP（24 / 32 位）转成 PNG。"""
    size, w, h, _planes, bpp, comp = struct.unpack_from("<IiiHHI", d, 0)
    if bpp not in (24, 32) or comp not in (0, 3) or w <= 0 or h == 0:
        raise ValueError(f"认不出这张图（{bpp} 位，压缩方式 {comp}）")
    used = struct.unpack_from("<I", d, 32)[0] if size >= 36 else 0
    off = size + (12 if comp == 3 and size == 40 else 0) + used * 4
    top_down, h = h < 0, abs(h)
    step, stride = bpp // 8, ((w * bpp + 31) // 32) * 4
    if off + stride * h > len(d):
        raise ValueError("图不完整")
    rows = []
    for y in range(h):
        at = off + (y if top_down else h - 1 - y) * stride
        src = d[at:at + w * step]
        out = bytearray(w * 3)
        out[0::3], out[1::3], out[2::3] = src[2::step], src[1::step], src[0::step]   # BGR → RGB
        rows.append(b"\x00" + bytes(out))
    return png(w, h, b"".join(rows))


# ---------------------------------------------------------------- 剪贴板

def _read(fmt: int) -> bytes | None:
    h = _u.GetClipboardData(fmt)
    if not h:
        return None
    p = _k.GlobalLock(h)
    if not p:
        return None
    try:
        return ctypes.string_at(p, _k.GlobalSize(h))
    finally:
        _k.GlobalUnlock(h)


def clipboard_seq() -> int:
    return _u.GetClipboardSequenceNumber()


def clipboard_image() -> bytes | None:
    """剪贴板里有图就给 PNG，没有给 None。"""
    for _ in range(20):                    # 截图工具刚写完时剪贴板可能还被占着，稍等再开
        if _u.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        return None
    try:
        fmt = _u.RegisterClipboardFormatW("PNG")
        if fmt and _u.IsClipboardFormatAvailable(fmt):
            d = _read(fmt)
            if d and d.startswith(b"\x89PNG") and b"IEND" in d:
                return d[:d.rindex(b"IEND") + 8]          # 后面可能有补齐的空字节
        if _u.IsClipboardFormatAvailable(CF_DIB):
            d = _read(CF_DIB)
            if d:
                return dib_to_png(d)
        return None
    finally:
        _u.CloseClipboard()


# ---------------------------------------------------------------- 按键、文件夹

def _modifiers_down() -> bool:
    return any(_u.GetAsyncKeyState(v) & 0x8000 for v in VK.values())


def press(*vks: int) -> None:
    """替你按一组键：先等你手上的 Ctrl / Alt / Shift / Win 都松开（不然会按成别的组合），再依次按下、倒着松开。"""
    end = time.monotonic() + 3
    while _modifiers_down() and time.monotonic() < end:
        time.sleep(0.03)
    seq = [(v, 0) for v in vks] + [(v, 2) for v in reversed(vks)]      # 2 = KEYEVENTF_KEYUP
    arr = (_INPUT * len(seq))()
    for i, (v, flags) in enumerate(seq):
        arr[i].type = 1                                                  # INPUT_KEYBOARD
        arr[i].ki = _KEYBDINPUT(v, 0, flags | (1 if v in (VK["lwin"], VK["rwin"]) else 0), 0, 0)   # Win 键是扩展键
    if _u.SendInput(len(seq), arr, ctypes.sizeof(_INPUT)) != len(seq):
        raise OSError("按不下系统截图的快捷键")


def _known(a: int, b: int, c: int, d: tuple, fallback: str) -> Path:
    """系统文件夹在哪（可能被挪到 D 盘或 OneDrive）；不是 Windows 就用家目录下的同名文件夹。"""
    if not available():
        return Path.home() / fallback
    guid = _GUID(a, b, c, (ctypes.c_ubyte * 8)(*d))
    out = ctypes.c_wchar_p()
    if _s.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) != 0:
        return Path.home() / fallback
    try:
        return Path(out.value)
    finally:
        _ole.CoTaskMemFree(out)


def videos_dir() -> Path:
    """「视频」文件夹。"""
    return _known(0x18989B1D, 0x99B5, 0x455B, (0x84, 0x1C, 0xAB, 0x7C, 0x74, 0xE4, 0xDD, 0xFC), "Videos")


def downloads_dir() -> Path:
    """「下载」文件夹：浏览器下好的东西默认放这（文献下载清单从这捡）。"""
    return _known(0x374DE290, 0x123F, 0x4565, (0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B), "Downloads")


def default_record_dir() -> Path:
    """截图工具自动保存录屏的地方（它自己的默认）。"""
    return videos_dir() / "Screen Recordings"


# ---------------------------------------------------------------- 等一张截图 / 一段录屏

def _new_files(folder: Path, before: set[str], since: float, exts=VIDEO_EXTS) -> list[Path]:
    if not folder.is_dir():
        return []
    out = []
    for f in folder.iterdir():
        try:
            if f.suffix.lower() in exts and f.is_file() and f.name not in before and f.stat().st_mtime >= since - 2:
                out.append(f)
        except OSError:
            continue
    return sorted(out, key=lambda f: f.stat().st_mtime)


def wait_video(folder: Path, before: set[str], since: float, stop: threading.Event,
               timeout: float = VIDEO_WAIT, poll: float = 1.0, settle: float = 2.0) -> Path | None:
    """等录屏文件夹里出现新的视频，而且大小 settle 秒没再变（截图工具写完了）。"""
    return wait_file(folder, before, since, stop, VIDEO_EXTS, timeout, poll, settle)


def wait_file(folder: Path, before: set[str], since: float, stop: threading.Event, exts,
              timeout: float, poll: float = 1.0, settle: float = 2.0) -> Path | None:
    """等文件夹里出现新的某种文件，而且大小 settle 秒没再变（写完了）。浏览器没下完的是 .crdownload / .part，不算。"""
    end = time.monotonic() + timeout
    last: dict[str, tuple[int, float]] = {}                   # 名字 → (大小, 从什么时候起是这个大小)
    while not stop.wait(poll):
        now = time.monotonic()
        if now > end:
            return None
        for f in _new_files(folder, before, since, exts):
            try:
                n = f.stat().st_size
                with open(f, "rb"):
                    pass                                   # 还被截图工具占着写：打不开，下一轮再看
            except OSError:
                continue
            size, t0 = last.get(f.name, (-1, now))
            if n != size:
                last[f.name] = (n, now)
            elif n > 0 and now - t0 >= settle:
                return f
    return None


def wait_image(seq: int, stop: threading.Event, timeout: float = IMAGE_WAIT) -> bytes | None:
    """等剪贴板里来一张新的图（只看 seq 之后的）。"""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        stopped = stop.wait(0.25)
        now = clipboard_seq()
        if now != seq:
            img = clipboard_image()
            if img:
                return img
            seq = now                      # 剪贴板变了但不是图（比如复制了字）：接着等
        if stopped:
            return None
    return None


class Grabber:
    """一次只等一件：截图或者录屏。结果交给 on_image(png 字节) / on_video(视频路径)，在后台线程里跑。"""

    def __init__(self, on_image, on_video, record_dir):
        self.on_image, self.on_video, self.record_dir = on_image, on_video, record_dir
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.kind: str | None = None
        self.since: float | None = None

    def status(self) -> dict:
        return {"kind": self.kind, "since": self.since}

    def start(self, kind: str) -> dict:
        if kind not in ("image", "video"):
            raise ValueError("只有 image（截图）和 video（录屏）")
        if not available():
            raise RuntimeError("这台电脑叫不出系统截图")
        with self._lock:
            if self.kind:
                raise Busy("正在等你框选" if self.kind == "image" else "正在录屏")
            self.kind, self.since = kind, time.time()
            self._stop.clear()
        threading.Thread(target=self._run, args=(kind,), daemon=True).start()
        return self.status()

    def cancel(self) -> None:
        self._stop.set()

    def _run(self, kind: str) -> None:
        try:
            if kind == "image":
                seq = clipboard_seq()
                press(VK["lwin"], VK["shift"], 0x53)                        # Win+Shift+S
                img = wait_image(seq, self._stop)
                if img:
                    self.on_image(img)
            else:
                folder = Path(self.record_dir())
                before = {f.name for f in folder.iterdir()} if folder.is_dir() else set()
                since = time.time()
                press(VK["lwin"], VK["shift"], 0x52)                        # Win+Shift+R
                f = wait_video(folder, before, since, self._stop)
                if f:
                    self.on_video(f)
        except Exception as e:                                               # 别让后台线程悄悄死掉：记一笔
            print(f"[capture] {e}", file=sys.stderr)
        finally:
            with self._lock:
                self.kind = self.since = None
