"""Windows-only, read-only StarCraft window inventory; deliberate click-to-restore actions.

Never closes/terminates a client. Never enumerates a substitute PID if session data is stale.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes as wt
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
SW_RESTORE = 9
EVENT_OBJECT_NAMECHANGE = 0x800C
OBJID_WINDOW = 0
CHILDID_SELF = 0
_notified_titles: dict[int, str] = {}
if sys.platform == "win32":
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    u32 = ctypes.WinDLL("user32", use_last_error=True)
    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.OpenProcess.restype = wt.HANDLE
    k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
    k32.QueryFullProcessImageNameW.restype = wt.BOOL
    k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k32.GetExitCodeProcess.restype = wt.BOOL
    k32.GetProcessTimes.argtypes = [wt.HANDLE, ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME),
                                    ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME)]
    k32.CloseHandle.argtypes = [wt.HANDLE]
    cbtype = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    u32.EnumWindows.argtypes = [cbtype, wt.LPARAM]
    u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    u32.IsWindowVisible.argtypes = [wt.HWND]
    u32.IsWindowVisible.restype = wt.BOOL
    u32.IsIconic.argtypes = [wt.HWND]
    u32.IsIconic.restype = wt.BOOL
    u32.GetWindowTextLengthW.argtypes = [wt.HWND]
    u32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    u32.SetWindowTextW.argtypes = [wt.HWND, wt.LPCWSTR]
    u32.SetWindowTextW.restype = wt.BOOL
    u32.NotifyWinEvent.argtypes = [wt.DWORD, wt.HWND, ctypes.c_long, ctypes.c_long]
    u32.NotifyWinEvent.restype = None
    u32.GetForegroundWindow.restype = wt.HWND
    u32.GetWindowRect.argtypes = [wt.HWND, ctypes.c_void_p]
    u32.GetWindowRect.restype = wt.BOOL
    u32.ShowWindowAsync.argtypes = [wt.HWND, ctypes.c_int]
    u32.ShowWindowAsync.restype = wt.BOOL
    u32.SetForegroundWindow.argtypes = [wt.HWND]
    u32.SetForegroundWindow.restype = wt.BOOL


def _process_info(pid: int):
    if sys.platform != "win32" or not isinstance(pid, int) or pid <= 0:
        return None
    handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        code = wt.DWORD()
        if not k32.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != STILL_ACTIVE:
            return None
        buff = ctypes.create_unicode_buffer(32768)
        n = wt.DWORD(len(buff))
        if not k32.QueryFullProcessImageNameW(handle, 0, buff, ctypes.byref(n)):
            return None
        if Path(buff.value).name.casefold() != "starcraft.exe":
            return None
        created, exited, kernel, user = (wt.FILETIME() for _ in range(4))
        stamp = None
        if k32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                               ctypes.byref(kernel), ctypes.byref(user)):
            filetime = (created.dwHighDateTime << 32) | created.dwLowDateTime
            stamp = (filetime - 116444736000000000) / 10000000
        return {"path": buff.value, "created": stamp}
    finally:
        k32.CloseHandle(handle)


def _main_windows(pids: set[int]) -> dict[int, dict]:
    found = {}
    if sys.platform != "win32" or not pids:
        return found

    @cbtype
    def callback(hwnd, _lparam):
        owner = wt.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        pid = int(owner.value)
        if pid not in pids or not u32.IsWindowVisible(hwnd):
            return True
        length = u32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        buff = ctypes.create_unicode_buffer(length + 1)
        u32.GetWindowTextW(hwnd, buff, len(buff))
        title = buff.value
        if "Brood War" not in title and "StarCraft" not in title:
            return True
        found[pid] = {"hwnd": int(hwnd), "title": title, "minimized": bool(u32.IsIconic(hwnd))}
        return True

    u32.EnumWindows(callback, 0)
    return found


def read_session(root: Path) -> dict:
    try:
        data = json.loads((Path(root) / "session-match.json").read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def role_text(slot: int, session: dict) -> str:
    """Role is determined by launcher slot and the session's selected model, not GUI focus."""
    names = {"Human": "Human / 직접 플레이", "CoG": "Pluto CoG 2026", "V2": "Pluto 2.0"}
    if slot == 3:
        return "P3 | OBSERVER / 관전 전용 (AI 없음)"
    who = session.get("P1" if slot == 1 else "P2", "Unknown")
    controller = names.get(who, "설정 미확인")
    pos = "HOST / 방장" if slot == 1 else "JOIN / 참가자"
    return f"P{slot} | PLAYER / {pos} | {controller}"


def game_caption(slot: int, session: dict) -> str:
    return role_text(slot, session) + " | StarCraft Remastered"


def label_session_windows(root: Path, rows: list[dict] | None = None) -> list[str]:
    """Give each validated top-level game HWND a distinct Alt+Tab/title-bar caption.

    This changes only caption text, never user input, client memory, or session positions.
    Called by the GUI; a running game is not required and missing windows are skipped.
    """
    if sys.platform != "win32":
        return []
    if rows is None:
        rows = inspect_session(root)
    session = read_session(root)
    updated = []
    for row in rows:
        if not row.get("active") or not row.get("window") or not row.get("hwnd"):
            continue
        caption = game_caption(row["slot"], session)
        original = row.get("title") or ""
        if original != caption:
            if not u32.SetWindowTextW(wt.HWND(row["hwnd"]), caption):
                continue
            updated.append(caption)
        # External SetWindowTextW changes GetWindowText, but Explorer's preview
        # may cache the old caption. Issue a one-shot accessibility name-change
        # event for this verified game HWND to invite UI consumers to refresh.
        # This is best-effort: taskbar refresh is not guaranteed by the API.
        hwnd = int(row["hwnd"])
        if _notified_titles.get(hwnd) != caption:
            u32.NotifyWinEvent(EVENT_OBJECT_NAMECHANGE, wt.HWND(hwnd),
                               OBJID_WINDOW, CHILDID_SELF)
            _notified_titles[hwnd] = caption
    return updated


class WindowRect(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def active_game_window(rows: list[dict]) -> tuple[dict, tuple[int, int, int, int]] | None:
    """Only return the foreground HWND when it belongs to this validated game session."""
    if sys.platform != "win32":
        return None
    foreground = int(u32.GetForegroundWindow() or 0)
    for row in rows:
        if row.get("active") and row.get("window") and row.get("hwnd") == foreground:
            rect = WindowRect()
            if u32.GetWindowRect(wt.HWND(foreground), ctypes.byref(rect)):
                return row, (rect.left, rect.top, rect.right, rect.bottom)
    return None


def inspect_session(root: Path) -> list[dict]:
    session = read_session(root)
    keys = ("P1Pid", "P2Pid", "ObserverPid")
    saved = {}
    for key in keys:
        try:
            saved[key] = int(session[key]) if session.get(key) is not None else None
        except (ValueError, TypeError):
            saved[key] = None
    start = None
    try:
        start = datetime.fromisoformat(session["Started"]).timestamp()
    except (ValueError, KeyError, TypeError):
        pass
    process = {key: _process_info(pid) if pid else None for key, pid in saved.items()}
    for key in keys:
        item = process[key]
        if item is not None and start is not None and item["created"] is not None:
            # Prevent recycled PID or a process from a different game session being targeted.
            if abs(item["created"] - start) > 180:
                process[key] = None
    windows = _main_windows({pid for key, pid in saved.items() if pid is not None and process[key] is not None})
    rows = []
    for index, key in enumerate(keys, 1):
        pid = saved[key]
        item = process[key]
        window = windows.get(pid) if item else None
        rows.append({
            "slot": index,
            "pid": pid,
            "active": item is not None,
            "window": window is not None,
            "minimized": bool(window and window["minimized"]),
            "hwnd": window["hwnd"] if window else None,
            "title": window["title"] if window else None,
            "label": ("미설정" if pid is None else
                      "종료/다른 세션" if item is None else
                      "창 확인 안 됨" if window is None else
                      "최소화됨" if window["minimized"] else "표시 중"),
        })
    return rows


def restore_window(root: Path, slot: int) -> str:
    """Call only from a real GUI button click; requires a verified same-session client."""
    if slot not in (1, 2, 3):
        return "잘못된 슬롯"
    row = inspect_session(root)[slot - 1]
    if not row["active"] or not row["window"]:
        return f"P{slot} 창이 실행 중이지 않습니다."
    hwnd = wt.HWND(row["hwnd"])
    u32.ShowWindowAsync(hwnd, SW_RESTORE)
    if not u32.SetForegroundWindow(hwnd):
        return f"P{slot} 창 복원을 요청했지만 Windows가 전면 전환을 제한했습니다."
    return f"P{slot} 창을 전면으로 요청했습니다."
