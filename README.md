Pikachu Desktop Pet - Windows

RUN FROM SOURCE
1. pip install PySide6 pygetwindow pynput
2. Keep pet.py and the sprites/ folder together (same directory).
3. Run: python pet.py

BUILD AS .exe
PyInstaller has to run on Windows itself (it doesn't cross-compile), so:
1. Copy this whole folder (pet.py, pet.spec, build.bat, sprites\) onto a
   Windows machine.
2. Double-click build.bat (or run it from a terminal).
3. Your standalone exe appears at dist\PikachuPet.exe — the sprites are
   bundled inside it, so that one file is all you need to share/run.

Behavior:
- Idles on screen, occasionally wanders + jumps onto another window's title bar.
- Left-drag to move it, double-click to make it dance, right-click for a menu
  (Dance / Charge up / Happy / Quit).
- States: idle (Animated_Sticker), happy (happy_anything_is_possible), charging
  (pokemon_charging_up), dancing (Dance_Dancing_Sticker) - swap the files in
  sprites/ any time to reskin it.
