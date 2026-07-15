# Checklist para publicar no GitHub

## Publicar

Arquivos recomendados para subir:

- `README-PUBLICACAO-GITHUB.md`
- `NOTAS-TECNICAS-FIRMWARE.md`
- `POC-REVISOES-E-TESTES.md`
- `EDMD-Cover-Pack-Tool-README.md`
- `tools/edmd_cover_pack_gui.py`
- `tools/scimg_tool.py`
- `tools/sc2p_tool.py`
- `tools/edmd_build_cover_pack.py`
- `tools/edmd_build_cover_pack_paged_h160.py`
- `tools/edmd_bulk_convert_covers_h160.py`
- `tools/edmd_build_browser_cover_pack_scp2_root_all_letters_poc135_h160_fatstate_wide_instagram_readable_y1_at.py`
- `tools/edmd_make_poc135_language_variants.py`
- `EDMD-Cover-Pack-Tool.spec`
- `sega-mega-drive-removebg-preview.ico`

Opcional:

- `EDMD-Cover-Pack-Tool.exe`, se voce quiser distribuir a ferramenta pronta.
- `patches/*.json`, se quiser deixar os offsets documentados em formato legivel por script.

## Nao publicar

Evite subir arquivos proprietarios ou dumps:

- `os-v36.bin`
- `os-v36-RESTORE-OFFICIAL.bin`
- `M29W640-DUMP-COPYCART-WORKING.BIN`
- `M29W640-DUMP-COPYCART-WORKING.wordswap.bin`
- `M29W640-extract-*.bin`
- `M29W640-PATCHED-*.bin`
- `OS-UPDATE-clone-main-*.bin`
- `POC*.BIN`
- `*.PAK` gerados a partir de capas de terceiros
- dumps de ROMs comerciais

## `.gitignore` sugerido

```gitignore
# Firmware/dumps proprietarios ou derivados
*.bin
*.BIN
M29W640-*
os-v36*.bin
OS-UPDATE-*.bin
POC*.BIN

# Packs e capas geradas
*.PAK
*.SCIMG
*.scimg
converted-covers/
cover-tool-output/
previews/
cover-crops.json

# Build de ferramenta
build/
dist/
__pycache__/
*.pyc

# Backups locais
firmware-backups/
sd-pack-backups/
tool-backups/
BACKUP-*/
POC-STABLE-BACKUP*/
POC-BACKUP*/

# Anexos/temporarios
.codex-remote-attachments/
*.log
```

Se voce quiser publicar exemplos, crie exemplos pequenos e livres, sem capas comerciais e sem ROMs comerciais.

## Estrutura sugerida do repositorio

```text
.
├── README.md
├── docs/
│   ├── NOTAS-TECNICAS-FIRMWARE.md
│   └── POC-REVISOES-E-TESTES.md
├── tools/
│   ├── edmd_cover_pack_gui.py
│   ├── scimg_tool.py
│   ├── sc2p_tool.py
│   ├── edmd_build_cover_pack.py
│   ├── edmd_build_cover_pack_paged_h160.py
│   ├── edmd_bulk_convert_covers_h160.py
│   ├── edmd_build_browser_cover_pack_scp2_root_all_letters_poc135_h160_fatstate_wide_instagram_readable_y1_at.py
│   └── edmd_make_poc135_language_variants.py
├── patches/
│   └── *.json
└── EDMD-Cover-Pack-Tool-README.md
```

Voce pode renomear `README-PUBLICACAO-GITHUB.md` para `README.md` quando for montar o repositorio publico.
