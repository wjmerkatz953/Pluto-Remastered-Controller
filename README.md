# Pluto Remastered Controller

**Windows GUI for StarCraft: Remastered matches featuring Pluto CoG 2026, Pluto 2.0, humans, and an optional dedicated spectator.**

![Pluto AI](https://img.shields.io/badge/AI-Pluto%202.0-blue) ![Windows](https://img.shields.io/badge/platform-Windows-lightgrey) ![license](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange)

> [!IMPORTANT]
> This is an **unofficial, noncommercial source-available** research/hobby project. It does **not** include StarCraft, Pluto model weights, inference programs, third-party game bridge binaries, or a one-click cross-PC installer.

## What works

- Native PySide6 GUI with per-player selection: **Human / Pluto CoG 2026 / Pluto 2.0**.
- Local/private LAN **P1 host vs P2 join**, with optional independent x64 **P3 Observer**.
- Single-PC **Pluto 2.0 vs Pluto 2.0** in StarCraft: Remastered.
- Distinct P1/P2/P3 window titles, OS-window inspection and per-window focus buttons.
- Pinned game/model/bridge SHA-256 integrity checks before starting clients.
- GUI build recipe for a standalone Windows executable (Qt GUI only).
- Private LAN match hosting and starting are currently **manual**; no Battle.net automation.

### Actual gameplay validation

On one Windows 11 PC with **StarCraft: Remastered 1.23.10.13515** using **Fighting Spirit 1.3 Melee**, the developer completed **two Pluto 2.0 mirror matches**, observing both to the end from the **third client configured in-game as an Observer**. The losing Pluto GG/left; the bridge recorded game-end winner/loser events. Results are not a universal compatibility guarantee.

## Setup (source release)

**Git clone alone cannot run the game.** Third-party assets must be supplied separately. This public project is an independent **Git repository**, not a fork of or replacement for the upstream game/AI/bridge repositories.

Required sibling layout:

```text
StarCraft/
  Pluto-Remastered-Controller/       # this repository
    Start-Pluto-Match.ps1
    pluto_arena_gui.py
    build-v2/Release/               # locally supplied bridge; gitignored
  pluto-remastered-1v1-main/        # upstream CoG launcher + setup
  pluto-v2.0/                       # official Pluto 2.0 release
```

1. Install your separately licensed **StarCraft: Remastered 1.23.10.13515**.
2. Obtain and set up the [single-PC CoG launcher](https://github.com/minsminsKR/pluto-remastered-1v1) as the sibling `pluto-remastered-1v1-main`; its `Setup.cmd` prepares the compatible launcher assets, map, configuration and CoG release.
3. Obtain the official [Pluto v2.0 model](https://github.com/tscmoo/pluto) as sibling `pluto-v2.0` with `pluto.dll` and `pluto/pluto_infer.exe` and `pluto/pluto_weights.bin`.
4. Provide a **compatible, separately built/obtained** Remastered V2 bridge and loader under the **untracked** paths `build-v2/Release/pluto-scr.dll` and `build-v2/Release/scr-loader.exe`. The pinned SHA-256 checks reject mismatching components. **The public CoG bridge cannot be assumed to support Pluto 2.0 unchanged.** Building the exact V2 bridge is not yet documented as a standalone reproducible public step.
5. Install Python and PySide6 and launch the GUI:

```powershell
python -m pip install -r requirements.txt
python pluto_arena_gui.py
```

Or build your own PyInstaller GUI using `python build_gui_exe.py`. No original game/model assets are included in the EXE.

Select **P1**, **P2** and optionally **P3 Observer**, click **환경 검사 (Verify)** and then **대전 실행 (Launch)**. In game, P1 creates the private LAN Melee room, P2 joins as a second PLAYER, and P3 must join an **OBSERVER** slot (not a third PLAYER slot).

GUI preferences use a project-specific Qt settings namespace. Starting the GUI from this repository uses the repository's own match session and runtime folders. The original development launcher folder is not changed.

## Development tests

```powershell
python test_match_selector.py
python test_role_titles.py
python test_crossprocess_window_title.py
python test_pluto_arena_gui.py  # includes VerifyOnly and requires local upstream files
python test_gui_preview.py
python build_gui_exe.py
python test_frozen_gui.py
```

Tests/verification do not create an actual match. Tests may create a throwaway Win32 dummy window, but never close existing StarCraft processes.

## Noncommercial license

Original project code is licensed under [PolyForm Noncommercial 1.0.0](LICENSE.md); see [NOTICE.md](NOTICE.md) for rights and third-party components. **Commercial use is not permitted** without a separate agreement. This is not an OSI-approved open-source license.

Commercial licensing inquiries: GitHub Issues. This is not an official Pluto AI or Blizzard product.
