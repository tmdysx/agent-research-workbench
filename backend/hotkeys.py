"""全局快捷键：在哪个软件里按都行，一键截图 / 录屏进随堂笔记（像微信的 Alt+A）。

作者 2026-09-27：要全局快捷键，「这些快捷键要在设置里可以设置」。
默认 Ctrl+Alt+S 截图、Ctrl+Alt+R 录屏——避开了微信 Alt+A、QQ Ctrl+Alt+A。
用 Windows 自己的 RegisterHotKey：挂在一个自己的线程上，这个线程转着收消息；改了设置就在那个线程里重新挂。
被别的程序占了（或者同时开着两个项目，先开的那个拿走了）就报「被占」，不硬抢。
只在正式启动时挂；自动测试不挂，免得占了你电脑上的快捷键。
"""
from __future__ import annotations

import ctypes
import queue
import sys
import threading

DEFAULTS = {"shot": "Ctrl+Alt+S", "record": "Ctrl+Alt+R"}
NAMES = ("shot", "record")
_MODS = {"ctrl": 0x2, "alt": 0x1, "shift": 0x4, "win": 0x8}
_ORDER = ("Ctrl", "Alt", "Shift", "Win")
MOD_NOREPEAT = 0x4000
WM_HOTKEY, WM_APP = 0x0312, 0x8000


def parse(text: str) -> tuple[int, int] | None:
    """「Ctrl+Alt+S」→ (修饰键, 键码)；空的 = 不用快捷键，给 None。写得不对抛 ValueError（消息给人看）。"""
    parts = [x.strip() for x in (text or "").replace("＋", "+").split("+") if x.strip()]
    if not parts:
        return None
    *mods, key = parts
    m = 0
    for x in mods:
        if x.lower() not in _MODS:
            raise ValueError(f"「{x}」不是 Ctrl / Alt / Shift / Win")
        m |= _MODS[x.lower()]
    if not m & (_MODS["ctrl"] | _MODS["alt"] | _MODS["win"]):
        raise ValueError("快捷键要带上 Ctrl、Alt 或 Win，不然平常打字会误触")
    k = key.upper()
    if len(k) == 1 and (k.isascii() and k.isalnum()):
        vk = ord(k)
    elif k.startswith("F") and k[1:].isdigit() and 1 <= int(k[1:]) <= 12:
        vk = 0x70 + int(k[1:]) - 1
    else:
        raise ValueError(f"「{key}」当不了快捷键：用一个字母、数字或者 F1–F12")
    return m, vk


def fmt(text: str) -> str:
    """整理成统一的写法：「alt+ctrl+s」→「Ctrl+Alt+S」；空的给空。"""
    p = parse(text)
    if p is None:
        return ""
    m, vk = p
    key = chr(vk) if vk < 0x70 else f"F{vk - 0x70 + 1}"
    return "+".join([x for x in _ORDER if m & _MODS[x.lower()]] + [key])


class Hotkeys:
    """一个线程专门收快捷键消息。apply() 换一套键，返回每个是「在用 / 被占 / 不用」。"""

    def __init__(self, on_fire):
        self.on_fire = on_fire                   # on_fire("shot" | "record")
        self.status = {n: "off" for n in NAMES}
        self._jobs: queue.Queue = queue.Queue()
        self._tid = None
        self._ready = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()
        self._ready.wait(3)

    def apply(self, keys: dict) -> dict:
        """keys = {"shot": "Ctrl+Alt+S", "record": ""}；在收消息的那个线程里重新挂。"""
        if not self._tid:
            return self.status
        done = threading.Event()
        self._jobs.put((keys, done))
        ctypes.windll.user32.PostThreadMessageW(self._tid, WM_APP, 0, 0)
        done.wait(3)
        return dict(self.status)

    def stop(self) -> None:
        if self._tid:
            ctypes.windll.user32.PostThreadMessageW(self._tid, 0x0012, 0, 0)     # WM_QUIT

    def _run(self) -> None:
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        u.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        msg = wintypes.MSG()
        u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)                          # 先把消息队列建出来
        self._tid = ctypes.windll.kernel32.GetCurrentThreadId()
        self._ready.set()
        try:
            while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and 1 <= msg.wParam <= len(NAMES):
                    name = NAMES[msg.wParam - 1]
                    threading.Thread(target=self._fire, args=(name,), daemon=True).start()
                elif msg.message == WM_APP:
                    while not self._jobs.empty():
                        keys, done = self._jobs.get()
                        for i in range(1, len(NAMES) + 1):
                            u.UnregisterHotKey(None, i)
                        for i, n in enumerate(NAMES, 1):
                            try:
                                p = parse(keys.get(n, ""))
                            except ValueError:
                                p = None
                            if p is None:
                                self.status[n] = "off"
                            else:
                                ok = u.RegisterHotKey(None, i, p[0] | MOD_NOREPEAT, p[1])
                                self.status[n] = "on" if ok else "taken"
                        done.set()
        finally:
            for i in range(1, len(NAMES) + 1):
                u.UnregisterHotKey(None, i)

    def _fire(self, name: str) -> None:
        try:
            self.on_fire(name)
        except Exception as e:                  # 正在等上一张、电脑叫不出截图……记一笔，不让线程死
            print(f"[hotkeys] {name}: {e}", file=sys.stderr)
