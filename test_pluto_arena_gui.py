"""Offscreen UI/CLI smoke test; never starts StarCraft."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from pluto_arena_gui import Arena, power_shell_args, log_summary

assert QApplication.instance() is None
app = QApplication(sys.argv)
QSettings.setDefaultFormat(QSettings.IniFormat)
settings_dir = tempfile.TemporaryDirectory(prefix="pluto-arena-test-")
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, settings_dir.name)
ui = Arena()
assert ui.card1.selected in ("Human","CoG","V2")
assert ui.card2.selected in ("Human","CoG","V2")
assert "선수 1" in ui.card1.layout().itemAt(0).widget().text()
assert "선수 2" in ui.card2.layout().itemAt(0).widget().text()
assert "AI 없음" in ui.observer.toolTip()
assert "관전자" in ui.observer.text()
assert "역할 배지" in ui.show_badge.text()
assert ui.role_badge.width() > 0
assert not ui.role_badge.isVisible()
ui.card1.combo.setCurrentIndex(ui.card1.combo.findData("CoG"))
ui.card2.combo.setCurrentIndex(ui.card2.combo.findData("V2"))
ui.observer.setChecked(True)
ui.english.setChecked(True)
args = power_shell_args(ui.root,"CoG","V2",True,True,True)
assert args[-2:] == ["-Observer", "-VerifyOnly"]
assert "-Language" in args and "English" in args
assert ui.root.joinpath("Start-Pluto-Match.ps1").is_file()
summary = log_summary(ui.root)
assert "P1:" in summary and "P2:" in summary
print("PASS: Qt widgets, model selection, English, observer, paths, recent logs",flush=True)

# Integration test real PowerShell -VerifyOnly, using QProcess's async GUI signals.
# This does not start game processes.
ui._run(True)
def finish():
    if ui.active_process is not None:
        print("FAIL: PowerShell verification timed out",flush=True)
        ui.active_process.kill()
        raise SystemExit(1)
    contents = ui.console.toPlainText()
    assert "PASS" in contents, contents[-4500:]
    assert ui.verify.isEnabled()
    assert ui.start.isEnabled()
    assert "환경 검사 PASS" in ui.status.text(), ui.status.text()
    print("PASS: GUI QProcess integration runs pinned SHA verification",flush=True)
    app.quit()
QTimer.singleShot(14000, finish)
app.exec()
settings_dir.cleanup()
