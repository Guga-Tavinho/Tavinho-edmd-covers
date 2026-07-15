# EDMD Cover Pack Tool

Ferramenta externa para gerar os arquivos `.PAK` usados pela firmware POC117-H160 do EverDrive-MD clone.

## Créditos

A ferramenta possui um botão `Créditos` no topo da janela, com links clicáveis para contato.

Firmware de capas e ferramenta por: Tavinho Games

- Instagram: `instagram.com/tavinho.games`
- YouTube: `youtube.com/@tavinho-games`

## Como usar

1. Execute `EDMD-Cover-Pack-Tool.bat`.
2. Em `Pasta das ROMs`, escolha a raiz onde estao as ROMs. Pode ser o SD ou uma pasta local com a mesma organizacao.
3. Em `Pasta das capas`, escolha a pasta com PNG/JPG.
4. Opcional: clique em `Editor de recorte` para ajustar o enquadramento de capas especificas.
5. Em `Destino dos .PAK`, escolha a raiz do SD ou uma pasta local.
6. Clique em `Gerar .PAK`.

## Editor de recorte

O editor de recorte salva os enquadramentos no arquivo `cover-crops.json`.

- Se uma capa tiver recorte salvo, a conversao usa esse enquadramento.
- Se uma capa nao tiver recorte salvo, a conversao usa o recorte automatico centralizado.
- O quadro de recorte sempre segue a proporcao final da capa do Mega Drive, 128x160.
- Arraste o quadro para escolher o enquadramento.
- Use a roda do mouse ou os botoes de zoom para aproximar/afastar.

## Modos de associacao

Com `Nome relativo` marcado, a ferramenta usa o modo inteligente:

- ignora maiuscula/minuscula, espacos e pontuacao;
- tenta casar pelo titulo base;
- pode usar a mesma capa para variantes quando `Associar capa a variantes do mesmo jogo` estiver marcado.

Com `Nome relativo` desmarcado, a ferramenta usa nome identico:

- `Aladdin (USA).png` casa com `Aladdin (USA).bin`;
- `Aladdin.png` nao casa com `Aladdin (USA).bin`;
- a comparacao ignora apenas maiuscula/minuscula e a extensao.

A ferramenta gera `0.PAK` e/ou `A.PAK` ate `Z.PAK`. A firmware escolhe o pack pela primeira letra do nome da ROM, nao pelo nome da pasta:

- `3 Ninjas Kick Back (USA).bin` usa `0.PAK`
- `Aladdin (USA).bin` usa `A.PAK`
- `Sonic The Hedgehog (USA).bin` usa `S.PAK`

## Ajuste manual

Quando uma capa nao casar automaticamente, rode a ferramenta uma primeira vez e abra a pasta de relatorio. Ela cria:

- `unmatched-roms.txt`
- `unmatched-images.txt`
- `cover-map-template.csv`
- `conversion-report.json`

Para forcar associacoes, crie/edite um CSV com colunas `cover,rom`:

```csv
cover,rom
Aladdin.png,01 A/Aladdin (USA).bin
Sonic.png,S/Sonic The Hedgehog (USA).bin
```

Depois selecione esse CSV no campo `Mapa manual CSV (opcional)` e gere novamente.

## Limites atuais

- A firmware atual trabalha com packs na raiz do SD: `0.PAK`, `A.PAK` ... `Z.PAK`.
- Cada pack foi preparado para ate 150 capas.
- A capa convertida para o Mega Drive fica em 128x160 pixels, 16 cores.
- Para adicionar ou corrigir capas, normalmente basta atualizar os `.PAK`; nao precisa atualizar a firmware.
