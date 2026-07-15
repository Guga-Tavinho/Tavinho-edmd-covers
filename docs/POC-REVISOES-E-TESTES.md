# Revisoes de POC e resultados de teste

Este arquivo resume as principais POCs criadas durante o desenvolvimento. Existem muitos arquivos intermediarios; a tabela abaixo registra as etapas que mudaram a direcao tecnica ou que foram validadas/rejeitadas no hardware.

## Regra de seguranca aplicada em todas as POCs

- Nao escrever em `0x0000`.
- Nao tocar no OS de recuperacao.
- Trabalhar somente no banco principal da OS.
- Gerar sempre arquivos de 64 KiB.
- Manter backups de POCs estaveis.
- Preferir testes incrementais pequenos.

## Linha do tempo resumida

| POC | Objetivo | Resultado em hardware | Observacao |
| --- | --- | --- | --- |
| Text-only inicial | Validar update sem mexer no recovery | Funcionou | Carregava jogos e mantinha update OS. |
| POC 1/2 | Hook simples no menu/toolbox | Falhou/tela preta em algumas tentativas | Mostrou que hook cedo demais era arriscado. |
| POC 3 | Preservar toolbox e abrir select game original | Funcionou parcialmente | Confirmou que nao se deveria remover toolbox. |
| POC 4 a 18 | Testes minimos de VDP/SD/browser | Variado: tela preta, quadrados, cores | Serviram para mapear onde desenhar sem travar. |
| POC 19 a 35 | Leitura manual de arquivo `.SCIMG` | Variado | Muitos travamentos por estado FAT/stack. |
| POC 36 a 49 | Diagnostico do registro selecionado no browser | Variado | Ajudou a entender onde estava o nome/registro do item selecionado. |
| POC 50 a 61 | Desenho de SCIMG/tile linear no browser | Evoluiu de lixo visual para imagem reconhecivel | Confirmou ordem de tiles e posicao da capa. |
| POC 62/63 | Capa dinamica e limpeza manual | Funcionou como base | Ainda dependia de acionamento e tinha problemas ao voltar. |
| POC 64 a 70 | Preservacao de estado FAT e capa automatica conhecida | Alguns travamentos | Mostrou que ler SD durante browser corrompia estado interno. |
| POC 71 a 75 | Cover pack inicial e limpeza quando nao ha capa | POC75 virou ponto estavel | Mostrou capa automatica por pack simples. |
| POC 76/77/78 | Testes 120x160 e 112x144 | 112x144 chegou a quebrar boot | Marcadas como perigosas em alguns casos. |
| POC 79 a 81 | Teste com mais paletas | Imagem pior/lavada | Abandonado; conversao de imagem era o gargalo real. |
| POC 82 a 87 | Packs numericos e navegacao automatica | POC87 estavel | Base para auto-carregamento com menos travamento. |
| POC 88 a 96 | Limpeza ao voltar e primeira capa da pasta | Variado | Corrigiu rastros/prints da capa na tela. |
| POC 97 a 101 | Pack por nome normalizado (`SCPK`) | Evoluiu, mas ainda limitado | Estabeleceu a ideia de catalogo por nome. |
| POC 102 a 104 | Teste com 70 capas | Funcionou apos ajustes | Confirmou necessidade de catalogo paginado. |
| POC 105/106 | Teste com 2200 capas em pack unico | Funcionou, mas deixou outras pastas lentas | Pack unico muito grande nao era caminho ideal. |
| POC 107 a 112 | Packs por letra e primeiros testes reais | Funcionou parcialmente | Algumas capas erradas por match/ordem, corrigido na ferramenta. |
| POC 113/114 | Altura 120/128 | Funcionou | Imagem ainda menor que desejado. |
| POC 115/116 | 112x160 | Teve barra/corte lateral | Abandonado como padrao final. |
| POC 117-H160 | 128x160 | Funcionou e ficou visualmente melhor | Virou base visual de capa. |
| POC 118 a 124 | Tentativas de melhorar navegacao rapida/debounce | Pouca melhora ou travamentos | Mantido comportamento estavel em vez de arriscar. |
| POC 125 | Cursor no topo ao trocar pagina | Funcionou | Patch em `0x6934` e `0x69A8`. |
| POC 126 | About personalizado | Funcionou | Alterou creditos para Tavinho Games. |
| POC 127 | Remover logo GAMEJOY84 pulando bloco | Quebrou botao de voltar no About | Metodo rejeitado por pular cleanup de stack. |
| POC 128 | Remover logo GAMEJOY84 com NOP so na chamada | Funcionou | Metodo correto: NOP em `0x7606`, stack preservada. |
| POC 129 | Mover packs para `/PAKS` | Travou file browser | Rejeitado; packs voltaram para raiz do SD. |
| POC 130 | Texto Instagram no browser com fonte OS | Funcionou, mas texto grande | Base para experimentar credito no browser. |
| POC 131 | Fix FAT/state amplo | Funcionou | Corrigiu travamento ao entrar em `OS UPDATE` depois do browser. |
| POC 132 | Instagram 2 tiles abaixo | Funcionou | Ainda usava fonte grande do OS. |
| POC 133 | Fonte pequena 3x5 | Funcionou, mas quase ilegivel | Muito espremida em CRT. |
| POC 134 | Fonte custom 5x7 | Funcionou e ficou legivel | Melhor equilibrio visual. |
| POC 135 | Texto correto com `@tavinho.games` | Funcionou | Base final. |
| POC135-PTBR | Traducao PT-BR | Funcionou | Textos revisados para evitar abreviacoes ruins. |
| POC135-ES | Traducao ES | Funcionou | Ajustes equivalentes ao PT-BR. |

## POCs perigosas ou rejeitadas

Alguns testes foram mantidos no historico, mas nao devem ser usados como base:

- POC que escreve ou altera regioes iniciais da OS.
- POCs marcadas com `DANGER`.
- POC 78/82 em certos testes de tamanho/pack.
- POC 109, que passou de uma area segura e quebrou boot.
- POC 127, que removeu o logo do About pulando stack cleanup.
- POC 129, que tentou usar `/PAKS` e travou o browser.

## Pontos de virada

### 1. Preservar toolbox

Uma tentativa inicial removeu funcoes do toolbox. Isso dificultava restaurar firmware pelo proprio cartucho. A partir dai virou regra: nunca quebrar toolbox/update/recovery.

### 2. Formato preconvertido

Ficou claro que o Mega Drive nao deveria decodificar imagem comum. A solucao foi criar `.SCIMG`/`.PAK`, ja em tiles e paleta prontos.

### 3. Packs por letra

Um pack unico com muitas capas funcionava, mas deixava navegacao lenta em pastas sem capa. A divisao por `0.PAK` e `A.PAK`..`Z.PAK` resolveu melhor.

### 4. Estado FAT

O bug mais importante apareceu na POC128: depois de usar o browser e carregar capas, voltar ao menu principal e entrar em `OS UPDATE` travava. A POC131 corrigiu isso ampliando o backup/restauracao do estado FAT/browser.

### 5. Fonte custom do Instagram

A fonte do OS era grande. A fonte 3x5 ficou ilegivel. A fonte 5x7 da POC134 ficou boa e virou base da POC135.

## Revisoes finais

### POC135 base

Arquivo:

- `OS-UPDATE-clone-main-poc135-h160-fatstate-wide-instagram-readable-y1-at-about-nologo.bin`

Caracteristicas:

- base POC131 com fix FAT;
- capa 128x160;
- texto `Siga no instagram: @tavinho.games`;
- fonte 5x7;
- About Tavinho Games;
- logo GAMEJOY84 removido com NOP seguro.

### POC135-PTBR

Arquivo:

- `OS-UPDATE-clone-main-poc135-PTBR.bin`

Textos principais:

- `Jogar ROM`
- `Selecionar`
- `Opcoes`
- `Truques`
- `Extras`
- `Apagando`
- `Carregando`
- `Atualizar SO`

### POC135-ES

Arquivo:

- `OS-UPDATE-clone-main-poc135-ES.bin`

Textos principais:

- `Jugar ROM`
- `Seleccionar`
- `Opcion`
- `Trucos`
- `Extras`
- `Borrando`
- `Cargando`
- `Actualizar SO`

## Teste final recomendado

Para validar uma nova build:

1. Atualizar pelo menu `OS UPDATE`.
2. Reiniciar.
3. Abrir file browser.
4. Entrar em uma pasta com ROMs.
5. Passar por ROMs com capa e sem capa.
6. Confirmar que a capa aparece e limpa corretamente.
7. Usar esquerda/direita para trocar pagina.
8. Confirmar que o cursor volta ao topo da pagina.
9. Pressionar `B` para voltar ao menu principal.
10. Entrar em `OS UPDATE`.
11. Confirmar que nao trava.
12. Entrar em `Toolbox > About`.
13. Confirmar creditos e botao de voltar.

## Observacao sobre os testes

Os resultados acima foram obtidos em hardware real com clone chines de EverDrive-MD V2. Em outro clone, revisao de PCB ou flash diferente, o comportamento pode variar.
