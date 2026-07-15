# Notas tecnicas da firmware

## Modelo de patch

A firmware nao foi reescrita do zero. Ela foi construida como patch da OS v36 principal do EverDrive-MD V2.

O fluxo dos scripts e:

1. Ler `M29W640-extract-os_bank_10000.bin`.
2. Validar bytes antigos em offsets conhecidos.
3. Aplicar patches pequenos no codigo original.
4. Inserir codigo 68000 novo em `0x9C00`.
5. Aplicar textos/creditos.
6. Validar tamanho final de 64 KiB.
7. Validar que o codigo injetado termina antes de `0xA800`.
8. Gerar `.BIN` de update.

## Hook do browser

O hook principal fica em `0x65E2`, substituindo:

```asm
move.w $FFE30C,d0
```

por:

```asm
bsr.w $FF9C00
nop
```

A rotina injetada termina restaurando a leitura original:

```asm
move.w $FFE30C,d0
rts
```

Assim o fluxo original do browser continua recebendo o estado esperado do controle.

## Estado FAT/browser

Durante o desenvolvimento, abrir `.PAK` dentro do browser alterava estado global usado pela OS. Isso nao quebrava sempre o browser, mas causava travamento ao voltar ao menu principal e entrar em `OS UPDATE`.

A correcao validada na POC131 foi ampliar o backup/restauracao:

- antes: salvar `0x60` bytes a partir de `0xFFCC64`;
- depois: salvar `0x100` bytes a partir de `0xFFCC64`;
- tambem salvar/restaurar `0x40` bytes do header apontado por `0xFFCC7C`.

Esse ajuste virou a base das POCs finais.

## Posicionamento da capa

Configuracao final:

```text
PREVIEW_X = 24 tiles
PREVIEW_Y = 2 tiles
WIDTH     = 16 tiles
HEIGHT    = 20 tiles
```

Isso resulta em uma capa de 128x160 pixels.

Na TV CRT do teste, essa area ficou visualmente parecida com uma capa vertical no lado direito do file browser.

## Limite de codigo

O clone mostrou comportamento instavel quando a area injetada crescia demais. Um teste anterior que passou da regiao segura quebrou o boot antes do menu.

Por isso foi adotado limite empirico:

```text
codigo injetado deve terminar antes de 0xA800
```

Exemplos finais:

- POC131: codigo `0x9C00..0xA51D`.
- POC135 base: codigo `0x9C00..0xA797`.
- POC135 PT-BR: codigo `0x9C00..0xA797`.
- POC135 ES: codigo `0x9C00..0xA7B9`.

## Texto de Instagram no browser

A primeira tentativa usava a fonte padrao da OS. Funcionou, mas a fonte era grande.

Depois foi criada uma fonte custom pequena:

- POC133: fonte 3x5, ficou pequena demais e dificil de ler.
- POC134: fonte 5x7, ficou legivel.
- POC135: fonte 5x7 com `@tavinho.games`.

Para economizar espaco, a fonte 5x7 nao grava um tile novo para cada caractere repetido. O script monta tiles apenas para os caracteres unicos usados na frase e o tilemap reutiliza esses tiles.

## Formato `.SCIMG`

O `.SCIMG` e um formato intermediario proprio usado pela ferramenta:

- header com assinatura;
- largura/altura em tiles;
- paleta Genesis;
- dados de tiles 4bpp;
- opcionalmente tilemap;
- opcao linear para firmware ler em ordem de tela.

A firmware final trabalha com capas lineares ja prontas, para nao precisar reorganizar tiles no console.

## Formato `.PAK` / `SCP2`

Os `.PAK` usam catalogo `SCP2`.

Estrutura geral:

```text
Header:
  magic       = "SCP2"
  version     = 1
  count       = quantidade de capas
  entry_size  = tamanho de cada entrada
  index_size  = tamanho total do catalogo
  sector_size = 512

Catalogo:
  entradas com:
    key normalizada
    offset da capa
    tamanho
    CRC32

Payload:
  arquivos SCIMG alinhados em setores
```

A primeira pagina do catalogo comporta 10 entradas. Entradas adicionais continuam nos setores seguintes.

## Escolha do `.PAK`

A firmware escolhe o pacote pela primeira letra do nome da ROM selecionada:

- `0.PAK`: ROMs que comecam por numero;
- `A.PAK`: ROMs que comecam por A;
- `B.PAK`: ROMs que comecam por B;
- ...
- `Z.PAK`: ROMs que comecam por Z.

Isso independe da pasta onde a ROM esta. A ROM pode estar em qualquer diretorio, desde que o nome normalize para uma key existente no `.PAK` correspondente.

## Conversao de imagem

A conversao no PC faz:

1. Abrir PNG/JPG.
2. Aplicar recorte automatico ou manual.
3. Redimensionar para 128x160.
4. Quantizar para paleta Genesis de 16 cores.
5. Converter para tiles 4bpp.
6. Gerar `.SCIMG`.
7. Montar `.PAK`.

O Mega Drive nao faz decode de imagem comprimida.

## Traducoes

As variantes PT-BR e ES foram feitas com patch de strings e redirecionamento de ponteiros para strings que nao cabiam no espaco original.

Por seguranca, as traducoes usam ASCII sem acentos. A fonte original da OS nao foi expandida para caracteres acentuados.

Alguns termos tecnicos foram preservados:

- `FAT`;
- `SRAM`;
- `ROM`;
- `SPI`;
- `SMS`;
- `MD`;
- `MegaKey`;
- `SEGA`;
- caminhos como `/EDMD`.

## Arquivos principais

Scripts de firmware:

- `tools/edmd_build_browser_cover_pack_scp2_root_all_letters_poc135_h160_fatstate_wide_instagram_readable_y1_at.py`
- `tools/edmd_make_poc135_language_variants.py`

Scripts/ferramentas de capas:

- `tools/scimg_tool.py`
- `tools/edmd_build_cover_pack_paged_h160.py`
- `tools/edmd_bulk_convert_covers_h160.py`
- `tools/edmd_cover_pack_gui.py`

Executavel da ferramenta:

- `EDMD-Cover-Pack-Tool.exe`

## Restauracao

Durante os testes, sempre foi mantida uma firmware estavel anterior e o recovery OS do cartucho.

Se uma POC falhar:

1. Desligar o console.
2. Ligar segurando `A+B+C`.
3. Entrar no sistema de recuperacao.
4. Restaurar uma firmware estavel.

Essa regra foi essencial no desenvolvimento.
