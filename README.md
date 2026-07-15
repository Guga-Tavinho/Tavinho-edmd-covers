# Firmware de capas para EverDrive-MD V2

Este projeto documenta e automatiza uma modificacao experimental da OS v36 do EverDrive-MD V2 para clones chineses, adicionando exibicao automatica de capas no file browser.

O trabalho foi feito sem o codigo-fonte original da OS do EverDrive-MD. A firmware final e resultado de engenharia reversa, patch binario controlado e codigo 68000 injetado em uma area livre da OS principal.

# Créditos

Firmware de capas e ferramenta por: Tavinho Games

    Instagram: instagram.com/tavinho.games
    YouTube: youtube.com/@tavinho-games

## Limite de capas

Na versão atual da firmware, cada arquivo `.PAK` suporta até **150 capas**.

Os packs são separados pela primeira letra ou número do nome da ROM:

- `0.PAK` para jogos que começam com número.
- `A.PAK` até `Z.PAK` para jogos que começam com letras.

Isso permite até **4050 capas no total**:    


# Recursos implementados:

- Exibicao automatica de capas ao navegar sobre ROMs `.bin`.
- Capa em 128x160 pixels, equivalente a 16x20 tiles do Mega Drive.
- Ferramenta externa para converter capas PNG/JPG e montar os `.PAK`.
- Editor visual de recorte/enquadramento.
- Variantes PT-BR e ES.
- Correção da troca de página no file browser: ao avançar/voltar página, o cursor volta para o primeiro item da página.

## Base tecnica

Base usada durante o desenvolvimento:

- OS v36 EverDrive-MD V2.x.
- Imagem principal de 64 KiB extraida do banco principal: `M29W640-extract-os_bank_10000.bin`.
- Base de execucao aparente: `0xFF0000`.
- Area de codigo injetado usada: a partir de `0x9C00`.
- Limite empirico de seguranca: manter o fim do codigo abaixo de `0xA800`.

Regra de seguranca principal:

- A area inicial da flash e o sistema de recuperacao nunca devem ser tocados.
- O desenvolvimento sempre trabalhou em cima do banco principal da OS.
- O recovery/OS reserva do clone foi preservado para permitir restauracao pressionando `A+B+C` ao ligar o console.

## Linguagens e ferramentas usadas

Linguagens:

- Python 3: geradores de firmware, conversores de imagem, criador de `.PAK`, GUI e scripts de validacao.
- Assembly Motorola 68000: codigo injetado na firmware, gerado como bytes pelos scripts Python.
- Tkinter: interface grafica da ferramenta de capas.
- PowerShell: automacao local, copia para SD e verificacoes.

Bibliotecas/ferramentas:

- Pillow: leitura, recorte, redimensionamento, quantizacao e preview de imagens.
- Capstone: disassembly e validacao dos trechos 68000.
- PyInstaller: empacotamento da ferramenta como `.exe`.
- Hash SHA-256: validacao de arquivos locais e copiados para o SD.

## Engenharia reversa usada

O processo comecou com a OS v36 em binario, sem source. A engenharia reversa foi feita por:

- varredura de strings ASCII para localizar menus, mensagens e rotinas;
- disassembly 68000 em big-endian;
- identificacao de tabelas de ponteiros de textos;
- identificacao de rotinas FAT/SD ja existentes na OS;
- identificacao de rotinas de texto/tela/VDP;
- testes incrementais em hardware real;
- validacao visual;
- comparacao byte a byte entre POCs estaveis e novas POCs.

Offsets importantes:

- `0x65E2`: hook usado depois do repaint do file browser.
- `0x6934` e `0x69A8`: ajuste para cursor voltar ao topo ao trocar pagina.
- `0x7606`: chamada que desenhava o logo grande `GAMEJOY84` no About; substituida por NOPs preservando o cleanup de stack.
- `0x9C00`: inicio do codigo injetado.
- `0xA800`: limite empirico de seguranca para nao quebrar boot no clone.
- `0xFFCC64`: bloco de estado FAT/browser salvo e restaurado.
- `0xFFCC7C`: ponteiro de buffer/header de diretorio salvo e restaurado.

## Como a firmware funciona

O file browser original continua sendo desenhado pela OS. Depois que o browser repinta a lista, o hook chama o codigo injetado:

1. Salva registradores 68000.
2. Salva estado interno do FAT/browser.
3. Verifica se o item selecionado parece uma ROM `.BIN`.
4. Decide qual `.PAK` abrir pela primeira letra do nome da ROM:
   - numeros usam `0.PAK`;
   - `A` usa `A.PAK`;
   - `B` usa `B.PAK`;
   - e assim por diante ate `Z.PAK`.
5. Busca a capa pelo nome normalizado dentro do catalogo `SCP2`.
6. Se encontrar, le a imagem `.SCIMG` ja convertida.
7. Copia paleta/tiles para o VDP e desenha a capa no lado direito do browser.
8. Se nao encontrar capa, limpa a area da capa.
9. Restaura o estado FAT/browser e os registradores.
10. Volta para o fluxo original da OS.

A firmware nao decodifica PNG/JPG. Toda conversao pesada fica no PC, na ferramenta externa.

## Formato das capas

Formato final exibido no console:

- resolucao: 128x160 pixels;
- tiles: 16x20;
- cores: 16 cores em uma paleta Genesis;
- tiles 4bpp no formato do VDP do Mega Drive;
- arquivo intermediario: `.SCIMG`;
- pacote final no SD: `.PAK` com catalogo `SCP2`.

Os `.PAK` ficam na raiz do SD:

```text
0.PAK
A.PAK
B.PAK
...
Z.PAK
```

Para adicionar ou corrigir capas, basta gerar novamente os `.PAK`. Nao e necessario atualizar a firmware.

## Ferramenta de capas

Arquivo principal:

- `EDMD-Cover-Pack-Tool.exe`

Fonte:

- `tools/edmd_cover_pack_gui.py`

Funcoes:

- seleciona pasta de ROMs;
- seleciona pasta de capas;
- associa capa por nome relativo ou nome identico;
- permite CSV manual para associacoes especificas;
- possui editor de recorte 128x160;
- gera previews no PC;
- gera `.PAK` por letra;
- possui interface em portugues, ingles e espanhol;
- possui creditos e links.

## Resultado final

A POC final validada foi a familia POC135:

- capas automaticas funcionando;
- navegacao do browser funcionando;
- volta por `B` funcionando;
- troca de paginas ajustada;
- entrada em `OS UPDATE` funcionando mesmo depois de usar o browser;
- About personalizado funcionando;
- texto de Instagram legivel;
- variantes PT-BR e ES funcionando.

Veja tambem:

- `POC-REVISOES-E-TESTES.md`
- `NOTAS-TECNICAS-FIRMWARE.md`
