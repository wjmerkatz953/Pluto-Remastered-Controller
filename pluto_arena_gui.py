"""Pluto Arena — native Qt control panel for an existing PRIVATE LAN launcher.

GUI only: no bundled StarCraft binary, bridge, model or game assets.
Do not change or bypass the original launcher's integrity checks.
"""
from __future__ import annotations

import codecs
import json
import os
import shutil
import sys
import time
from pathlib import Path

from PySide6.QtCore import QProcess, QSettings, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QPainter, QPen
from arena_window_control import (inspect_session, restore_window, label_session_windows, active_game_window, role_text, read_session)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGraphicsDropShadowEffect,
    QGridLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QTextEdit, QVBoxLayout, QWidget
)

APP_TITLE = "Pluto Arena"
MODEL_TYPES = (("사람 (직접 플레이)", "Human"), ("Pluto CoG 2026", "CoG"), ("Pluto 2.0", "V2"))
DARK = "#090F17"
MUTED = "#8798AB"
ACCENT = "#56DFC0"
DEFAULT_MATCH_ROOT = Path(__file__).resolve().parent
MAX_LOG_CHARS = 20000

STYLE = """
QMainWindow, QWidget#main { background: #090F17; color: #ECF4FA; }
QWidget { color: #E7EFF5; font-family: 'Segoe UI', 'Malgun Gothic'; font-size: 13px; }
QLabel#eyebrow { color: #56DFC0; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#bigTitle { font-size: 29px; font-weight: 800; color: #F3FAFF; }
QLabel#subtitle { color: #93A6B9; font-size: 12px; }
QLabel#cardTag { color: #56DFC0; font-size: 11px; font-weight: 700; }
QLabel#cardTitle { font-size: 18px; font-weight: 750; color: #F1F7FC; }
QLabel#cardDetail { color: #A0B7C8; font-size: 11px; }
QLabel#roleHeading { color: #EAF8F5; font-size: 12px; font-weight: 700; }
QLabel#roleHelp { color: #9EAFBD; font-size: 11px; }
QLabel#vs { color: #56DFC0; font-size: 20px; font-weight: 800; }
QLabel#sectionTitle { font-size: 14px; font-weight: 700; }
QLabel#sectionNote, QLabel#pathText { color: #8295A8; font-size: 11px; }
QLabel#statusText { color: #BCD1DF; font-size: 12px; }
QFrame#panel { background: #111C28; border: 1px solid #243648; border-radius: 16px; }
QFrame#modelCard { background: #121F2B; border: 1px solid #31485A; border-radius: 15px; }
QFrame#settingsCard { background: #101B26; border: 1px solid #243648; border-radius: 13px; }
QComboBox { background: #1C2C3B; border: 1px solid #395064; border-radius: 9px;
  padding: 9px 12px; color: #F2F7FB; min-height: 22px; selection-background-color: #2B675B; }
QComboBox:hover, QComboBox:focus { border: 1px solid #56DFC0; }
QComboBox::drop-down { border: none; width: 25px; }
QComboBox QAbstractItemView { background: #172633; color: #EDF6FC; selection-background-color: #27564C; }
QCheckBox { spacing: 10px; font-weight: 600; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #547082;
  border-radius: 5px; background: #162433; }
QCheckBox::indicator:checked { background: #56DFC0; border: 1px solid #56DFC0; }
QPushButton { background: #1B2B3A; color: #EAF2F9; border: 1px solid #395063;
  border-radius: 9px; min-height: 35px; padding: 4px 13px; font-weight: 650; }
QPushButton:hover { background: #273F50; border-color: #56DFC0; }
QPushButton:pressed { background: #1C3541; }
QPushButton:disabled { background: #15202B; color: #687C8E; border-color: #253541; }
QPushButton#startButton { background: #53DDB9; color: #092320; border: 1px solid #53DDB9;
  min-height: 44px; font-weight: 800; font-size: 15px; }
QPushButton#startButton:hover { background: #85ECD1; }
QPushButton#startButton:disabled { background: #244B45; color: #70988B; border-color: #244B45; }
QPushButton#verifyButton { border-color: #3B6A69; }
QTextEdit#log { background: #080F17; border: 1px solid #273947; border-radius: 10px;
  color: #BBD5CF; font-family: 'Consolas', 'D2Coding', monospace; font-size: 11px;
  padding: 8px; selection-background-color: #27564C; }
QScrollBar:vertical { background: #0A131C; width: 9px; margin: 4px 0; }
QScrollBar::handle:vertical { background: #385265; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""


def match_root_from_settings(settings: QSettings | None = None) -> Path:
    if settings is not None:
        saved = str(settings.value("match_root", "")).strip()
        if saved:
            return Path(saved)
    override = os.environ.get("PLUTO_MATCH_ROOT", "").strip()
    if override:
        return Path(override)
    current = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    if (current / "Start-Pluto-Match.ps1").is_file():
        return current
    return DEFAULT_MATCH_ROOT


def power_shell_args(root: Path, p1: str, p2: str, observer: bool, english: bool, verify: bool) -> list[str]:
    args = [
        "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", str(root / "Start-Pluto-Match.ps1"),
        "-P1", p1, "-P2", p2,
        "-Language", "English" if english else "Default",
    ]
    if observer:
        args.append("-Observer")
    if verify:
        args.append("-VerifyOnly")
    return args


def log_summary(root: Path) -> str:
    output = []
    for index in (1, 2):
        folder = root / f"match-player{index}"
        bridge = folder / "bridge.log"
        if not bridge.is_file():
            output.append(f"P{index}: 기록 없음")
            continue
        # Read only tail to keep GUI responsive after long matches.
        with bridge.open("rb") as fd:
            fd.seek(0, 2)
            fd.seek(max(0, fd.tell() - 160_000))
            lines = fd.read().decode("utf-8", errors="replace").splitlines()
        model = "모델 미확인"
        end = ""
        start = ""
        cmd = False
        for line in lines:
            if '"stage":"model_confirmed"' in line:
                try:
                    model = json.loads(line).get("model", model)
                except ValueError:
                    pass
            if '"stage":"session_accepted"' in line:
                start = "게임 참가 승인"
            if '"stage":"model_first_command"' in line:
                cmd = True
            if '"stage":"match_end"' in line:
                try:
                    event = json.loads(line)
                    end = "승리" if event.get("winner") else "패배"
                    end += f" · F{event.get('frame', '?')}"
                except ValueError:
                    end = "경기 종료"
        output.append(f"P{index}: {model} | {end or ('명령 전송 확인' if cmd else start or '로그 확인 필요')}")
    return "\n".join(output)


class StatusDot(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(13, 13)
        self._color = QColor("#788B9F")

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#142530"), 1))
        painter.setBrush(self._color)
        painter.drawEllipse(1, 1, 11, 11)


class ModelCard(QFrame):
    def __init__(self, slot: str, initial: str, parent=None):
        super().__init__(parent)
        self.setObjectName("modelCard")
        self.setMinimumHeight(162)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 17)
        layout.setSpacing(8)

        flag = QLabel("P" + str(int(slot)) + ("  ·  선수 1  /  방장" if slot == "01" else "  ·  선수 2  /  참가자"))
        flag.setObjectName("cardTag")
        layout.addWidget(flag)

        self.model_name = QLabel("사람이 직접 조종")
        self.model_name.setObjectName("cardTitle")
        layout.addWidget(self.model_name)

        self.description = QLabel("")
        self.description.setObjectName("cardDetail")
        layout.addWidget(self.description)
        self.combo = QComboBox()
        for title, key in MODEL_TYPES:
            self.combo.addItem(title, userData=key)
        self.combo.setCurrentIndex(next(i for i in range(self.combo.count()) if self.combo.itemData(i) == initial))
        self.combo.currentIndexChanged.connect(self._update)
        layout.addWidget(self.combo)
        self._update()

    @property
    def selected(self) -> str:
        return str(self.combo.currentData())

    def _update(self, *_):
        names = {"Human": "직접 플레이", "CoG": "AI · Pluto CoG 2026", "V2": "AI · Pluto 2.0"}
        hints = {
            "Human": "조종: 사람  /  AI 브리지 없음",
            "CoG": "조종: Pluto AI  /  CoG 모델",
            "V2": "조종: Pluto AI  /  2.0 모델",
        }
        self.model_name.setText(names[self.selected])
        self.description.setText(hints[self.selected])


class Arena(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("window")
        self.setWindowTitle("Pluto Arena  |  StarCraft Remastered")
        self.setMinimumSize(900, 780)
        self.resize(1060, 900)
        self.setStyleSheet(STYLE)
        self.settings = QSettings("PlutoRemasteredController", "Launcher")
        self.root = match_root_from_settings(self.settings)
        self.active_process: QProcess | None = None
        self.active_mode = None
        self._expected_observer = False
        self._observer_watch_until = 0.0
        self._observer_missing_reported = False
        self._output_decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self._output_tail = ''
        self._window_rows = []
        self._last_role_hwnd = None
        self._badge_until = 0.0
        self._build()
        self._append("PLUTO ARENA / PRIVATE LAN MATCH CONTROL")
        self._append(f"실행기 경로: {self.root}")
        self._append("실제 게임 실행 전 '환경 검사'를 권장합니다.")
        self._restore()
        self._update_paths()
        self._init_role_badge()
        self._window_timer = QTimer(self)
        self._window_timer.setInterval(2000)
        self._window_timer.timeout.connect(self._refresh_window_status)
        self._window_timer.start()
        self._refresh_window_status()
        self._role_timer = QTimer(self)
        self._role_timer.setInterval(300)
        self._role_timer.timeout.connect(self._tick_role_badge)
        self._role_timer.start()

    def _build(self):
        widget = QWidget()
        widget.setObjectName("main")
        self.setCentralWidget(widget)
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(28, 18, 28, 18)
        outer.setSpacing(12)

        top = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        eyebrow = QLabel("STARCRAFT REMASTERED   /   LOCAL LAN LAB")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("PLUTO   ARENA")
        title.setObjectName("bigTitle")
        subtitle = QLabel("선수 2명(P1/P2) + 선택적 관전자(P3)  ·  선수마다 사람 또는 Pluto AI 지정")
        subtitle.setObjectName("subtitle")
        title_col.addWidget(eyebrow)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        top.addLayout(title_col, 1)

        status_group = QHBoxLayout()
        status_group.setSpacing(9)
        self.dot = StatusDot()
        self.status = QLabel("IDLE · 준비됨")
        self.status.setObjectName("statusText")
        status_group.addWidget(self.dot)
        status_group.addWidget(self.status)
        top.addLayout(status_group)
        outer.addLayout(top)

        match_panel = QFrame()
        match_panel.setObjectName("panel")
        card_row = QHBoxLayout(match_panel)
        card_row.setContentsMargins(14, 14, 14, 14)
        card_row.setSpacing(16)
        self.card1 = ModelCard("01", "Human")
        self.card2 = ModelCard("02", "V2")
        card_row.addWidget(self.card1, 1)
        versus = QLabel("VS")
        versus.setObjectName("vs")
        versus.setAlignment(Qt.AlignCenter)
        versus.setFixedWidth(48)
        card_row.addWidget(versus)
        card_row.addWidget(self.card2, 1)
        outer.addWidget(match_panel)

        settings = QFrame()
        settings.setObjectName("settingsCard")
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(21, 18, 21, 17)
        settings_layout.setSpacing(11)
        section = QLabel("MATCH OPTIONS")
        section.setObjectName("eyebrow")
        settings_layout.addWidget(section)

        toggles = QHBoxLayout()
        toggles.setSpacing(24)
        self.observer = QCheckBox("P3 관전자 창 켜기  /  직접 관전")
        self.english = QCheckBox("English UI 요청")
        self.show_badge = QCheckBox("창 전환 시 P1/P2/P3 역할 배지")
        self.observer.setToolTip("P3는 AI 없음 · 직접 관전하는 세 번째 x64 창입니다. LAN에서 Observer 슬롯을 수동 지정하세요.")
        self.english.setToolTip("실행 인자 --locale=enUS를 전달합니다. 실제 적용 여부는 게임에서 확인하세요.")
        toggles.addWidget(self.observer)
        toggles.addWidget(self.english)
        toggles.addWidget(self.show_badge)
        toggles.addStretch(1)
        settings_layout.addLayout(toggles)
        spectator = QLabel("P3 · 관전자 — AI 없음 / 조작할 군대 없음 / 승패에 참가하지 않음")
        spectator.setObjectName("roleHelp")
        spectator.setWordWrap(True)
        settings_layout.addWidget(spectator)

        note = QLabel("P1·P2는 선수 자리입니다. 각 선수의 조종 주체를 위에서 선택하세요.  /  LAN · Melee · 투혼 1.3")
        note.setObjectName("sectionNote")
        note.setWordWrap(True)
        settings_layout.addWidget(note)
        outer.addWidget(settings)

        actions = QHBoxLayout()
        actions.setSpacing(11)
        self.verify = QPushButton("환경 검사")
        self.verify.setObjectName("verifyButton")
        self.verify.clicked.connect(lambda: self._run(True))
        self.start = QPushButton("대전 실행   ▶")
        self.start.setObjectName("startButton")
        self.start.clicked.connect(lambda: self._run(False))
        actions.addWidget(self.verify, 1)
        actions.addWidget(self.start, 2)
        outer.addLayout(actions)

        window_panel = QFrame()
        window_panel.setObjectName("settingsCard")
        window_row = QHBoxLayout(window_panel)
        window_row.setContentsMargins(16, 10, 16, 10)
        window_row.setSpacing(12)
        window_heading = QLabel("WINDOWS")
        window_heading.setObjectName("eyebrow")
        window_row.addWidget(window_heading)
        self.window_labels = []
        self.window_buttons = []
        for slot in (1, 2, 3):
            label = QLabel(f"P{slot} · {'관전자' if slot == 3 else '선수'} · 확인 중")
            label.setObjectName("sectionNote")
            self.window_labels.append(label)
            window_row.addWidget(label, 1)
            button = QPushButton(f"P{slot} 보기")
            button.setMinimumHeight(27)
            button.clicked.connect(lambda _checked=False, number=slot: self._show_game_window(number))
            self.window_buttons.append(button)
            window_row.addWidget(button)
        outer.addWidget(window_panel)

        log_heading = QHBoxLayout()
        label = QLabel("ACTIVITY  /  실행 로그")
        label.setObjectName("sectionTitle")
        log_heading.addWidget(label)
        log_heading.addStretch(1)
        refresh = QPushButton("최근 경기 결과")
        refresh.clicked.connect(self._show_match_summary)
        folder = QPushButton("로그 폴더")
        folder.clicked.connect(self._open_log_folder)
        clear = QPushButton("지우기")
        clear.clicked.connect(self.console_clear)
        for button in (refresh, folder, clear):
            button.setMinimumHeight(29)
            log_heading.addWidget(button)
        outer.addLayout(log_heading)

        self.console = QTextEdit()
        self.console.setObjectName("log")
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(168)
        outer.addWidget(self.console, 1)

        foot = QHBoxLayout()
        self.path_label = QLabel("")
        self.path_label.setObjectName("pathText")
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        foot.addWidget(self.path_label, 1)
        select_root = QPushButton("실행기 위치 변경")
        select_root.clicked.connect(self._pick_root)
        foot.addWidget(select_root)
        outer.addLayout(foot)

    def _restore(self):
        self.card1.combo.setCurrentIndex(self.card1.combo.findData(self.settings.value("p1", "Human")))
        self.card2.combo.setCurrentIndex(self.card2.combo.findData(self.settings.value("p2", "V2")))
        self.observer.setChecked(str(self.settings.value("observer", "false")).lower() in ("true", "1"))
        self.english.setChecked(str(self.settings.value("english", "false")).lower() in ("true", "1"))
        self.show_badge.setChecked(str(self.settings.value("show_role_badge", "true")).lower() in ("true", "1"))

    def _save(self):
        self.settings.setValue("p1", self.card1.selected)
        self.settings.setValue("p2", self.card2.selected)
        self.settings.setValue("observer", self.observer.isChecked())
        self.settings.setValue("english", self.english.isChecked())
        self.settings.setValue("show_role_badge", self.show_badge.isChecked())
        self.settings.setValue("match_root", str(self.root))

    def _update_paths(self):
        self.path_label.setText(f"ENGINE   {self.root}")

    def _pick_root(self):
        chosen = QFileDialog.getExistingDirectory(self, "Start-Pluto-Match.ps1이 있는 폴더 선택", str(self.root))
        if chosen:
            self.root = Path(chosen)
            self._save()
            self._update_paths()
            self._append(f"실행기 위치 변경: {self.root}")

    def _set_status(self, msg: str, color: str = "#788B9F"):
        self.status.setText(msg)
        self.dot.set_color(color)

    def _append(self, line: str):
        self.console.append(line)
        plain = self.console.toPlainText()
        if len(plain) > MAX_LOG_CHARS:
            self.console.setPlainText(plain[-MAX_LOG_CHARS:])
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def console_clear(self):
        self.console.clear()

    def _init_role_badge(self):
        # A brief, click-through and no-focus hint when switching to a game window.
        # On exclusive fullscreen displays this overlay might not be visible;
        # Alt+Tab titles and the GUI role labels remain available.
        self.role_badge = QLabel("")
        self.role_badge.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput
        )
        self.role_badge.setAttribute(Qt.WA_TranslucentBackground, True)
        self.role_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.role_badge.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.role_badge.setFocusPolicy(Qt.NoFocus)
        self.role_badge.setAlignment(Qt.AlignCenter)
        self.role_badge.setFixedSize(500, 52)
        self.role_badge.setStyleSheet(
            "QLabel { background-color: rgba(8, 20, 32, 225); color: #EAFBF6;"
            "border: 2px solid #56DFC0; border-radius: 12px;"
            "font-size: 14px; font-weight: 750; padding: 8px; }"
        )
        self.role_badge.hide()

    def _tick_role_badge(self):
        if not self.show_badge.isChecked():
            self.role_badge.hide()
            self._last_role_hwnd = None
            return
        selected = active_game_window(self._window_rows)
        if not selected:
            self.role_badge.hide()
            self._last_role_hwnd = None
            return
        row, (left, top, right, bottom) = selected
        hwnd = row["hwnd"]
        if hwnd != self._last_role_hwnd:
            self._last_role_hwnd = hwnd
            self._badge_until = time.monotonic() + 3.3
            self.role_badge.setText(role_text(row["slot"], read_session(self.root)))
            self.role_badge.move(left + max(0, (right - left - self.role_badge.width()) // 2), top + 18)
            self.role_badge.show()
        elif time.monotonic() > self._badge_until:
            self.role_badge.hide()

    def _refresh_window_status(self):
        try:
            rows = inspect_session(self.root)
            self._window_rows = rows
            if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
                label_session_windows(self.root, rows)
            if self._observer_watch_until > time.monotonic() and not self._observer_missing_reported:
                observer = rows[2]
                if not observer["active"] or not observer["window"]:
                    self._observer_missing_reported = True
                    self._set_status("P3 관전자 창 종료/손실", "#F18A8A")
                    self._append("[WINDOW ERROR] P3 관전자 창이 시작 직후 종료되었거나 표시되지 않습니다.")
            for row, label, button in zip(rows, self.window_labels, self.window_buttons):
                who = '관전자' if row['slot'] == 3 else '선수'
                label.setText(f"P{row['slot']} {who} · {row['label']}")
                label.setToolTip(
                    f"PID: {row['pid'] if row['pid'] else '-'}  /  "
                    + role_text(row["slot"], read_session(self.root))
                )
                button.setEnabled(row["active"] and row["window"])
        except Exception as exc:
            for label, button in zip(self.window_labels, self.window_buttons):
                label.setText("창 상태 오류")
                button.setEnabled(False)

    def _show_game_window(self, slot: int):
        result = restore_window(self.root, slot)
        self._append("[WINDOW] " + result)
        self._refresh_window_status()

    def _show_match_summary(self):
        self._append("— 최근 경기 기록 —")
        self._append(log_summary(self.root))

    def _open_log_folder(self):
        if self.root.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root)))
        else:
            QMessageBox.warning(self, "경로 없음", "대전기 폴더가 존재하지 않습니다.")

    def _run(self, verify: bool):
        if self.active_process is not None:
            return
        if not (self.root / "Start-Pluto-Match.ps1").is_file():
            QMessageBox.warning(self, "실행기 없음",
                "선택한 경로에 Start-Pluto-Match.ps1이 없습니다.\n'실행기 위치 변경'에서 폴더를 선택하세요.")
            self._set_status("실행기 없음", "#F0AB65")
            return
        ps = shutil.which("powershell.exe")
        if not ps:
            QMessageBox.warning(self, "PowerShell 없음", "Windows PowerShell을 찾지 못했습니다.")
            return
        self._save()
        self._expected_observer = self.observer.isChecked()
        self._observer_watch_until = 0.0
        self._observer_missing_reported = False
        self._output_decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self._output_tail = ''
        p1, p2 = self.card1.selected, self.card2.selected
        args = power_shell_args(self.root, p1, p2, self.observer.isChecked(),
                                self.english.isChecked(), verify)
        self._append("")
        self._append(f"━━ {'VERIFY' if verify else 'LAUNCH'}  ·  {p1} VS {p2} ━━")
        self._append(f"선수1(P1, 방장) = {p1}  /  선수2(P2, 참가) = {p2}")
        self._append(f"관전자(P3)={'켜짐 / AI 없음' if self.observer.isChecked() else '꺼짐'}  /  영어={'ON' if self.english.isChecked() else 'OFF'}")
        self._set_status("환경 검사 중…" if verify else "게임 창 시작 중…", "#E6C36B")
        self.verify.setEnabled(False)
        self.start.setEnabled(False)
        proc = QProcess(self)
        self.active_process = proc
        self.active_mode = "verify" if verify else "launch"
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.setWorkingDirectory(str(self.root))
        proc.setProgram(ps)
        proc.setArguments(args)
        proc.readyReadStandardOutput.connect(self._read_output)
        proc.errorOccurred.connect(self._process_error)
        proc.finished.connect(self._process_finished)
        proc.start()

    def _read_output(self):
        if self.active_process is None:
            return
        data = bytes(self.active_process.readAllStandardOutput())
        if not data:
            return
        decoded = self._output_tail + self._output_decoder.decode(data).replace("\r\n", "\n")
        *lines, self._output_tail = decoded.split("\n")
        for line in lines:
            if line.strip():
                self._append(line)

    def _process_error(self, err: QProcess.ProcessError):
        self._append(f"[PROCESS ERROR] {err.name}")
        if err == QProcess.FailedToStart:
            self._end(False)

    def _process_finished(self, exit_code: int, _status):
        self._read_output()
        self._output_tail += self._output_decoder.decode(b'', final=True)
        if self._output_tail.strip():
            self._append(self._output_tail)
        self._output_tail = ''
        self._end(exit_code == 0)

    def _end(self, success: bool):
        mode = self.active_mode
        if self.active_process is None:
            return
        self.active_process.deleteLater()
        self.active_process = None
        self.active_mode = None
        self.verify.setEnabled(True)
        self.start.setEnabled(True)
        self._refresh_window_status()
        if success and mode == 'launch':
            rows = inspect_session(self.root)
            expected = rows if self._expected_observer else rows[:2]
            missing = [str(row['slot']) for row in expected if not row['active'] or not row['window']]
            if missing:
                success = False
                self._append(f"[WINDOW ERROR] P{', P'.join(missing)} 창이 현재 실행 중인지 확인되지 않습니다.")
                self._append("대전 실행기는 기존 창을 자동 종료하지 않습니다. WIN 상태를 확인하세요.")
        if success:
            if mode == "verify":
                self._set_status("환경 검사 PASS", "#56DFC0")
                self._append("[PASS] 파일 검증 완료 (게임 창은 실행하지 않음)")
            else:
                self._set_status("게임 창 실행 완료", "#56DFC0")
                if self._expected_observer:
                    self._observer_watch_until = time.monotonic() + 30.0
                self._append("[READY] P1 선수 창에서 PRIVATE LAN 방을 만들고 P2 선수 창으로 참가하세요.")
                if self._expected_observer:
                    self._append("[OBSERVER] P3는 AI 없는 관전 전용 창입니다. 참가 시 Observer 슬롯을 선택하세요.")
                self._append("실제 AI 행동 및 관전 기능은 인게임에서 확인해야 합니다.")
        else:
            self._set_status("실패 · 로그 확인", "#F18A8A")
            self._append("[FAILED] 위 오류 메시지를 확인하세요. 게임 창은 자동 종료하지 않습니다.")

    def closeEvent(self, event):
        self._save()
        if self.active_process is not None:
            QMessageBox.information(self, "작업 진행 중",
                "현재 검사 또는 실행 준비가 진행 중입니다.\n완료된 다음 GUI를 종료하세요.")
            event.ignore()
        else:
            self.role_badge.hide()
            self.role_badge.close()
            event.accept()


def main() -> int:
    preview = "--screenshot" in sys.argv
    check = "--self-test" in sys.argv
    if preview:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    # Background/offscreen Windows sessions may expose zero fonts to Qt.
    # Load local Windows fonts by path; no fonts are bundled or redistributed.
    fonts = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts'
    for name in ('segoeui.ttf', 'seguisb.ttf', 'malgun.ttf', 'arial.ttf', 'consola.ttf'):
        font_file = fonts / name
        if font_file.is_file():
            QFontDatabase.addApplicationFont(str(font_file))
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("PlutoArena")
    icon_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    icon_path = icon_root / 'pluto_arena.ico'
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    ui = Arena()
    if check:
        assert ui.card1.combo.count() == 3 and ui.card2.combo.count() == 3
        assert (ui.root / "Start-Pluto-Match.ps1").is_file()
        return 0
    ui.show()
    if preview:
        app.processEvents()
        target = Path(sys.argv[sys.argv.index("--screenshot") + 1])
        assert ui.grab().save(str(target), "PNG")
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
