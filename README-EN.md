<p align="right">
  <a href="./README.md">Português</a> |
  <strong>English</strong> |
  <a href="./README-ES.md">Español</a>
</p>

# Cover Art Firmware for EverDrive-MD V2

Modified firmware for the EverDrive-MD V2 that adds **game cover art directly to the file browser**, making SD card navigation more attractive, practical, and similar to modern flashcart menus.

The project includes the firmware with cover art support and a Windows tool capable of converting PNG/JPG images into `.PAK` files, which are used by the EverDrive to automatically display the cover corresponding to the selected game.

This work was created without access to the original EverDrive-MD OS source code. The final firmware is the result of reverse engineering.

<h2 align="center">🎥 Video Demonstration</h2>

<p align="center">
  <a href="https://www.youtube.com/watch?v=ZBZwvmXG3as&t=1s">
    <img
      src="https://i.imgur.com/IX8iTHN.jpeg"
      alt="Watch the video demonstration"
      width="700"
    >
  </a>
</p>

<p align="center">
  Click the image to watch it on YouTube.
</p>

# Credits

Cover art firmware and tool by: Tavinho Games

Follow on Instagram: **[@tavinho.games](https://instagram.com/tavinho.games)**  
Subscribe to the channel: **[youtube.com/@tavinho-games](https://youtube.com/@tavinho-games)**

## Cover Limit

In the current firmware version, each `.PAK` file supports up to **150 covers**.

The packs are separated according to the first letter or number in the ROM name:

- `0.PAK` for games whose names begin with a number.
- `A.PAK` through `Z.PAK` for games whose names begin with a letter.

This allows up to **4,050 covers in total**.

# Implemented Features

- Automatic cover display when browsing `.bin` ROMs.
- Covers displayed at 128x160 pixels, equivalent to 16x20 Mega Drive tiles.
- External tool for converting PNG/JPG covers and creating `.PAK` files.
- Visual cropping and framing editor.
- PT-BR and ES variants.
- Fixed page switching in the file browser: when moving to the next or previous page, the cursor returns to the first item on the page.

## How to Use

1. Copy the firmware `.BIN` file to the SD card.
2. On the EverDrive-MD, open the **OS Update** menu, select the file, and update using the modified firmware.
3. On the computer, open the **EDMD Cover Pack Tool**.
4. Select the folder containing the ROMs.
5. Select the folder containing the covers.
6. Choose the root of the SD card as the destination.
7. Click **Generate .PAK**.
8. Confirm that the files `0.PAK`, `A.PAK` through `Z.PAK` were generated in the root of the SD card.
9. Insert the SD card into the EverDrive-MD and open the file browser.
10. When the cursor is placed over a ROM with an associated cover, the cover will be displayed automatically.

## Technical Base

Base used during development:

- EverDrive-MD V2.x OS v36.
- Main 64 KiB image extracted from the primary bank: `M29W640-extract-os_bank_10000.bin`.
- Apparent execution base: `0xFF0000`.
- Injected code area used: starting at `0x9C00`.
- Empirical safety limit: keep the end of the code below `0xA800`.

Main safety rule:

- The initial flash area and the recovery system must never be modified.
- Development was always performed on the main OS bank.
- The clone's recovery/reserve OS was preserved, allowing restoration by holding `A+B+C` while powering on the console.

## Languages and Tools Used

Languages:

- Python 3: firmware generators, image converters, `.PAK` creator, GUI, and validation scripts.
- Motorola 68000 Assembly: code injected into the firmware and generated as bytes by Python scripts.
- Tkinter: graphical interface for the cover tool.
- PowerShell: local automation, SD card copying, and verification.

Libraries/tools:

- Pillow: image loading, cropping, resizing, quantization, and preview generation.
- Capstone: disassembly and validation of 68000 code sections.
- PyInstaller: packaging the tool as an `.exe`.
- SHA-256 hash: validation of local files and files copied to the SD card.

## Reverse Engineering Process

The process began with OS v36 in binary form, without source code. Reverse engineering was performed through:

- scanning ASCII strings to locate menus, messages, and routines;
- big-endian 68000 disassembly;
- identification of text pointer tables;
- identification of FAT/SD routines already present in the OS;
- identification of text, screen, and VDP routines;
- incremental testing on real hardware;
- visual validation;
- byte-by-byte comparison between stable POCs and new POCs.

Important offsets:

- `0x65E2`: hook used after the file browser repaint.
- `0x6934` and `0x69A8`: adjustments that return the cursor to the top when switching pages.
- `0x7606`: call that drew the large `GAMEJOY84` logo in the About screen; replaced with NOPs while preserving stack cleanup.
- `0x9C00`: start of the injected code.
- `0xA800`: empirical safety limit to avoid breaking boot on the clone.
- `0xFFCC64`: saved and restored FAT/browser state block.
- `0xFFCC7C`: saved and restored directory buffer/header pointer.

## How the Firmware Works

The original file browser continues to be drawn by the OS. After the browser repaints the list, the hook calls the injected code:

1. Saves the 68000 registers.
2. Saves the internal FAT/browser state.
3. Checks whether the selected item appears to be a `.BIN` ROM.
4. Determines which `.PAK` file to open based on the first character of the ROM name:
   - numbers use `0.PAK`;
   - `A` uses `A.PAK`;
   - `B` uses `B.PAK`;
   - and so on through `Z.PAK`.
5. Searches for the cover using the normalized name inside the `SCP2` catalog.
6. If found, reads the already-converted `.SCIMG` image.
7. Copies the palette/tiles to the VDP and draws the cover on the right side of the browser.
8. If no cover is found, clears the cover area.
9. Restores the FAT/browser state and the registers.
10. Returns to the original OS flow.

The firmware does not decode PNG/JPG files. All heavy conversion is performed on the PC by the external tool.

## Cover Format

Final format displayed on the console:

- resolution: 128x160 pixels;
- tiles: 16x20;
- colors: 16 colors in a Genesis palette;
- tiles: 4bpp in Mega Drive VDP format;
- intermediate file: `.SCIMG`;
- final SD card package: `.PAK` with an `SCP2` catalog.

The `.PAK` files are stored in the root of the SD card:

```text
0.PAK
A.PAK
B.PAK
...
Z.PAK
```

To add or correct covers, simply generate the `.PAK` files again. Updating the firmware is not required.

## Cover Tool

Main file:

- `EDMD-Cover-Pack-Tool.exe`

Source:

- `tools/edmd_cover_pack_gui.py`

Features:

- selects the ROM folder;
- selects the cover folder;
- matches covers by relative name or identical name;
- supports a manual CSV file for specific associations;
- includes a 128x160 crop editor;
- generates previews on the PC;
- generates `.PAK` files by letter;
- includes Portuguese, English, and Spanish interfaces;
- includes credits and links.

## Final Result

The validated final POC was the POC135 family:

- automatic covers working;
- browser navigation working;
- return with `B` working;
- page switching adjusted;
- access to `OS UPDATE` working even after using the browser;
- customized About screen working;
- readable Instagram text;
- PT-BR and ES variants working.

See also:

- `POC-REVISOES-E-TESTES.md`
- `NOTAS-TECNICAS-FIRMWARE.md`
