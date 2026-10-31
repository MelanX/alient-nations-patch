# Alien Nations (Die Völker) – resolution & controls patch

An unofficial patch for the 1999 strategy game **Alien Nations** (German: *Die Völker*),
GOG release **v2.05**. It adds widescreen resolutions up to 2560×1440, smoother map
scrolling and WASD controls.

The patch modifies your own copy of the game. **No game files are included in this repository.**

> **Note:** This patch was created with AI assistance:
> the reverse engineering, the code and this README. It was directed and play-tested by a
> human; see [Status](#status) for what has actually been tested.

## tl;dr (Linux)

```sh
git clone https://github.com/MelanX/alien-nations-patch.git
cd alien-nations-patch
python3 install.py "$HOME/Games/Heroic/Alien Nations" --ddraw   # path to your game folder
```

1. Tell Wine to use cnc-ddraw: in Heroic open the game settings → *Advanced* →
   *Environment variables* and add `WINEDLLOVERRIDES` = `ddraw=n,b`.
2. Start the game, go to *Optionen → Grafikeinstellungen* and click *Auflösung*.

Undo everything with `python3 install.py "<game folder>" --uninstall`.
Details, Windows and other launchers: see [Installation](#installation).

## What it does

| Change                                       | Details                                                                                                                                                                                                                                                                |
|----------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Higher resolutions**                       | The *Auflösung* toggle in *Optionen → Grafikeinstellungen* cycles through 800×600, 1024×768, 1280×720, 1600×900, 1920×1080 and 2560×1440 instead of only 800×600 and 1024×768. The label shows the selected size.                                                      |
| **Sidebar graphics for the new sizes**       | The game looks up the right-hand sidebar background by screen width (`INTERFACE800`, `INTERFACE1024`). The patch adds `INTERFACE1280/1600/1920/2560` to all three races (Amazons, Pimmons, Sajiki), built from the original 1024 graphic by extending its lower panel. |
| **Smoother scrolling**                       | The map scrolls in 8 ms steps instead of 25 ms, with sub-pixel movement, a gentler start (≈0.3 s ramp-up) and a lower top speed (≈810 px/s instead of ≈1280 px/s). Applies to arrow keys and to screen-edge scrolling.                                                 |
| **Mouse no longer stops keyboard scrolling** | In the original game, moving the mouse while holding an arrow key stopped the scrolling.                                                                                                                                                                               |
| **WASD**                                     | W/A/S/D work like the arrow keys. They are ignored while multiplayer chat (F1–F4) or the options menu is open, so typing doesn't move the map. The game has no letter hotkeys, so nothing is lost.                                                                     |
| **Version text fix**                         | The game stores the version text from `AlienNations_usa.ini` in an 8-byte buffer, so longer text got cut off and overwrote a neighbouring variable. The patch gives it its own 260-byte buffer.                                                                        |

### What it does *not* do

- **The main menu and videos stay at 800×600 / 640×480.** Their artwork is a fixed size;
  cnc-ddraw scales them to your screen.
- **The UI is not scaled.** Sprites, fonts and buttons are drawn at their original pixel size,
  so at 2560×1440 on a 1440p monitor the UI is small. For a bigger UI, pick a lower resolution
  and let cnc-ddraw upscale it, e.g. on a 2560×1440 monitor:

  | In-game resolution | UI size on screen         | Map area visible |
  |--------------------|---------------------------|------------------|
  | 2560×1440          | 1×                        | 100 %            |
  | 1920×1080          | 1.33×                     | 56 %             |
  | 1600×900           | 1.6×                      | 39 %             |
  | 1280×720           | 2× (sharp, exact scaling) | 25 %             |

- **It doesn't fix the black screen after Alt+Tab by itself.** cnc-ddraw fixes that (see below).

## Compatibility

Only the **GOG release v2.05 (German)** is supported. The installer checks the SHA-256 of
every file before changing anything, and every binary patch also verifies the original bytes.
On other versions it stops with an error and writes nothing.

| File                        | SHA-256 (original)                                                 |
|-----------------------------|--------------------------------------------------------------------|
| `Bin/AN.exe`                | `d58e6b895944915cd6f8ced82f70f7c516f07ac92d567b369afe4982b6d5e060` |
| `Data/AMAZONS/interface.gd` | `a49e3d7d979407a8e7834c700155ce3527712ac08744e84af23095dedc4e6fbe` |
| `Data/PIMONS/interface.gd`  | `cc3386b5c4249f47e002b47e142c62ae68d12fdd474ca0b5759caa8f4bd9e930` |
| `Data/SAJIKI/interface.gd`  | `25f73e75d5dc8b549ca36298b27fd1340b5f16ed40b1dab5b3661237e7c5c4b7` |

If you have another version (English, retail CD, ...) and want it supported, open an issue
with the SHA-256 of your `AN.exe`.

## Installation

You need **Python 3.7+** (standard library only). The patch also needs
**[cnc-ddraw](https://github.com/FunkyFr3sh/cnc-ddraw)**, which the installer can download for you.

Why cnc-ddraw: the game's own DirectDraw mode check would reject the new resolutions, so the
patch skips it and relies on cnc-ddraw to accept any size. cnc-ddraw also fixes the black
screen after Alt+Tab and scales the picture to your screen.

### 1. Run the installer

```sh
python3 install.py "/path/to/Alien Nations" --ddraw
```

On Windows: `py install.py "C:\GOG Games\Alien Nations" --ddraw`

The path is the folder that contains `Bin` and `Data`. What happens:

1. The installer checks that all game files are the original GOG v2.05 files.
2. With `--ddraw`, if there is no `Bin/ddraw.dll` yet, it downloads the latest `cnc-ddraw.zip`
   from the [official releases](https://github.com/FunkyFr3sh/cnc-ddraw/releases) and prints
   its version and SHA-256. This happens before anything is changed, so a failed download
   leaves the game untouched. An existing cnc-ddraw is kept as it is.
3. It patches `Bin/AN.exe` and the three `interface.gd` files, keeping the originals as
   `*.orig` next to them.
4. With `--ddraw`, it adds the cnc-ddraw files to `Bin/` (existing files are never
   overwritten) and sets the recommended options in `Bin/ddraw.ini`: borderless fullscreen,
   keep aspect ratio, accept all resolutions, OpenGL renderer with the FSR upscaling shader.
   A `ddraw.ini` you already had is backed up as `Bin/ddraw.ini.orig`.

Without `--ddraw` only the game files are patched; install and configure cnc-ddraw yourself
(extract `ddraw.dll`, `ddraw.ini` and `Shaders/` from `cnc-ddraw.zip` into `Bin/`).

Add `--dry-run` to see what would happen without writing anything.

### 2. Linux only: DLL override

Wine and Proton use their own `ddraw.dll` unless told otherwise. Set the DLL override
`ddraw` to `native,builtin` for the game:

- **Heroic:** game settings → *Advanced* → *Environment variables*: `WINEDLLOVERRIDES` = `ddraw=n,b`
- **Lutris:** game options → *System options* → *Environment variables*: `WINEDLLOVERRIDES` = `ddraw=n,b`
  (if the variable already exists, append `;ddraw=n,b`). Also turn off the Wine virtual
  desktop in the runner options; cnc-ddraw does its own borderless fullscreen.
- **Plain Wine:** `winecfg` → *Libraries* → add `ddraw` → *Native then Builtin*.

### 3. Choose a resolution

Start the game, open *Optionen → Grafikeinstellungen* and click *Auflösung* until the
resolution you want is shown. It takes effect when you start or continue a game.

### Optional: version text in the main menu

The main menu shows the version from `AlienNations_usa.ini` in the Windows folder
(`C:\Windows\`, or `drive_c/windows/` in the Wine prefix), section `[Info]`, key `Version`.
Change it to e.g. `Version=v2.05-patched` if you like. Thanks to the fix above, longer
text no longer gets cut off.

## Uninstall

```sh
python3 install.py "/path/to/Alien Nations" --uninstall
```

This restores the `*.orig` files and removes cnc-ddraw again if the installer added it
(it keeps a list in `Bin/cnc-ddraw.anpatch.json`). A `ddraw.ini` you had before is restored
from `Bin/ddraw.ini.orig`. If the saved resolution is not one the original game knows, it is
reset to 1024×768 (`Savegames/an.cfg`). On Linux you can remove the DLL override afterwards.

## Status

### Platforms

| Platform | Launcher / store                               | Status      |
|----------|------------------------------------------------|-------------|
| Linux    | Heroic Games Launcher, GOG version (GE-Proton) | ✅ tested   |
| Linux    | Lutris, Bottles, plain Wine                    | ⚠️ untested |
| Windows  | –                                              | ⚠️ untested |

Tested with the GOG German release v2.05 and cnc-ddraw 7.1 on Linux Mint.

### Features

- ✅ resolution toggle, playing at 1920×1080 and 2560×1440, Amazon sidebar
- ✅ installer, re-install, uninstall, cnc-ddraw download and error cases against the original files
- ✅ smooth scrolling, WASD and the version text fix in-game
- ⬜ Pimmon and Sajiki sidebars in-game
- ⬜ multiplayer

If you try it on an untested setup, please open an issue and say whether it worked.

## Customising

**Scroll speed:** `SCROLL_ACCEL` and `SCROLL_MAX` in `anpatch/exe.py`
(units: 1/16 px per 8 ms step). Re-run `install.py` afterwards; it always patches from the
`.orig` backups.

**Resolutions:** edit the table in `cave/cave.s` (`restab`, and the count `nres`), then run
`python3 tools/build_cave.py` (needs GNU binutils with i386 support: `as`, `ld`, `objcopy`)
and re-run `install.py`. Sidebars for new widths are generated automatically. Widths must be
unique (the sidebar is chosen by width); sidebar generation is tested for heights 720–1440. The
installer will mention that the output differs from the reference build; that's expected.

## How it works

The game (`AN.exe`, 32-bit, DirectDraw, 16-bit color) already computes most of its
in-game layout from the screen size (map = width − 192 px, sidebar = 192 px on the right).
Only a few places were hard-coded to 800/1024:

| Address                                        | Change                                                                                       |
|------------------------------------------------|----------------------------------------------------------------------------------------------|
| `0x42b0fd`                                     | resolution toggle calls `next_res` (cycles through a table) instead of switching 800↔1024    |
| `0x42b12e`                                     | ignore the DirectDraw display-mode list check                                                |
| `0x42b151`                                     | always mark the resolution as changed                                                        |
| `0x42b15a`, `0x42b644`, `0x42b6a5`             | resolution label: `"<w> X <h>"` via `wsprintfA`, wider text box                              |
| `0x484158`, `0x484173`, `0x484181`             | entering a game: switch to the configured mode if width ≠ 800 (was: width = 1024 → 1024×768) |
| `0x4298d6`                                     | closing the in-game options: same condition                                                  |
| `0x44453d`, `0x444520`, `0x4445f7`, `0x4afc08` | scrolling: 8 ms steps, velocity in 1/16 px with sub-pixel remainder, new speed constants     |
| `0x486989`, `0x4869e8`                         | mouse handler only stops scrolling if no scroll key is held                                  |
| `0x44008c`, `0x43ff06`                         | key-down/key-up dispatch: map W/A/S/D to the arrow keys                                      |
| `0x486d5e`, `0x428561`                         | version text buffer moved from an 8-byte global to a 260-byte one                            |

The new code (`cave/cave.s`, prebuilt as `anpatch/cave.bin`) goes into unused padding at the
end of the `.text` section (`0x4a4690`); the section headers of `.text` and `.data` are
enlarged to cover the new code and data. The selected resolution is saved by the game itself
in `Savegames/an.cfg`.

The sidebar backgrounds live in `Data/<race>/interface.gd`, a simple archive of RLE-compressed
32-bit sprites. `anpatch/gdfile.py` reads and rebuilds these archives, keeping all existing
data byte-for-byte; `anpatch/sidebar.py` decodes, extends and re-encodes the sprite. The
format is described in the docstrings of both files.

### Repository layout

```
install.py            installer / uninstaller
anpatch/exe.py        binary patch list for AN.exe
anpatch/cave.bin      assembled new code (built from cave/cave.s)
anpatch/gdfile.py     .gd archive reader/writer
anpatch/sidebar.py    sidebar sprite generation
cave/cave.s           source of the new code (GNU as, Intel syntax)
tools/build_cave.py   rebuilds anpatch/cave.bin and checks the entry points
```

## Credits

- [cnc-ddraw](https://github.com/FunkyFr3sh/cnc-ddraw) by FunkyFr3sh, which this patch relies on.
- Reverse engineering done with Ghidra.
- Built by MelanX together with Claude (Anthropic) in Claude Code. Claude analysed the game,
  wrote the patch, the installer and this README; MelanX steered it, tested in-game and
  reviewed the results. The installer verifies every file and byte it changes and keeps
  backups, but this is still a hobby project: keep your own backup of the game folder.

## License & disclaimer

The code in this repository is released under the [MIT License](LICENSE).

Alien Nations / Die Völker and all of its files belong to their respective rights holders.
This project is not affiliated with them or with GOG. Use at your own risk and keep your
backups.
