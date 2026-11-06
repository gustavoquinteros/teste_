# Relatório técnico — R2 "a IA escreve o script de layout do job"

Rodada R01 da bancada (06/11/2026). 6 peças-mestras × 5 formatos = 30 adaptações, um agente de IA por peça.
As seções 1 a 9 tratam só da **produção** (verificador automático e registros dos agentes). A seção 10 traz, à parte,
o resultado do júri cego, porque é dele que vem o número 29/30.

## 1. Resumo

- **Ideia:** para cada job, a IA lê a peça-mestra e **escreve um programa Python próprio** que calcula o layout dos 5 formatos e
  grava as peças. O mesmo verificador dos outros caminhos confere o resultado; a IA corrige o script e roda de novo.
- **Produção:** **30/30** peças passaram em todas as verificações duras, **todas já na 1ª verificação** de cada formato
  (segundo os registros dos 6 agentes). As verificações extras serviram só para melhorar qualidade.
- **Tentativas:** 45 de 90 permitidas (1,5 por peça). R8 usou 70.
- **Custo:** ~138 mil tokens e ~5,7 min por job (~27,7 mil tokens por peça). É o caminho mais caro e mais lento da bancada.
- **Código:** 2.063 linhas escritas no total (291 a 408 por job). **O código não se reaproveita:** de 30 tentativas de rodar o
  script de uma peça em outra, 2 rodaram e 0 de 10 peças passou no QA.
- **Saída:** a mesma IR (JSON) dos outros caminhos, que alimenta o mesmo verificador e o mesmo exportador do Motor InDesign.

## 2. Arquitetura

```
peça-mestra (IR JSON) + tabela de formatos + ativos
        │
        ▼
 agente de IA ── lê o KV (JSON + PNG) ── escreve runs/R01/scripts/R2/<peça>.py
        │                                        │
        │                                  roda o script
        │                                        ▼
        │                         5 candidatos (IR JSON), um por formato
        │                                        │
        └──── edita o script ◄── verificador (render Chromium + QA), até 3 vezes por formato
```

| Componente | Onde | Quem fez |
|---|---|---|
| Peça-mestra, formatos, ativos | `fixtures/`, `assets/assets.json` | bancada (os mesmos de todos os caminhos) |
| Script de layout do job | `runs/R01/scripts/R2/<peça>.py` | **a IA, um por job** |
| Verificador | `engine/lib.js` `B.checks` + `engine/pixel.py` | bancada |
| CLI de verificação | `node engine/bench.mjs check <candidato>` | bancada |

Regras impostas ao agente (`AGENT_BRIEF.md`): não pode usar o motor da bancada (`lib.js`) nem o comando `plan`; não pode reescrever
texto, trocar fonte, cor, peso ou ativo; não pode remover nem inventar elementos; no máximo 3 verificações por formato.

## 3. Como os scripts funcionam

Os 6 agentes chegaram, de forma independente, à mesma estrutura em 7 partes:

| # | Parte | O que faz | Exemplos nos scripts |
|---|---|---|---|
| 1 | Leitura | carrega a peça-mestra, formatos e ativos; separa elementos por `id` | `src_el`, `SRC`, `ASSETS` |
| 2 | **Medição de texto** | recria a medida do Chromium com PIL/raqm e as métricas verticais da fonte (ascent/descent da tabela hhea), compensando o glifo que vaza da linha com entrelinha 1,05 | `vmetrics`, `em_metrics`, `measure`, `font_file` |
| 3 | **Quebra de linha controlada** | escolhe a largura da caixa para o título quebrar onde o designer quebraria e evita palavra órfã; descarta larguras "no limite", onde PIL e Chromium podem quebrar diferente | `wrap`, `balanced`, `robust_width`, `fit_width` |
| 4 | Recorte da foto | janela "cover" sem distorção, posicionada para manter a área protegida (torres, piscina, sofá) | `cover_crop`, `hero_crop`, `protected_vis` |
| 5 | **Layout sob medida por formato** | uma função por formato, com a composição decidida para aquela peça | `lay_post`, `lay_card`, `L_banner`, `stories`, `banner` |
| 6 | **Autocrítica antes do check** | reimplementa parte do verificador (colisão, quase-alinhamento, área protegida, proporções) e corrige antes de gastar uma verificação | `report`, `near_pairs`, `selfcheck`, `critique`, `lint`, `preview` |
| 7 | Gravação | escreve os 5 JSON no esquema da bancada | `build`, `main` |

O que muda de job para job é a parte 5. Exemplos de decisões tomadas nos scripts:
- **bioma_produto:** post/e-mail em pilha (logo + título | foto sangrada | selo + CTA + legal); card com o painel verde ao lado da
  foto, como no KV; banner logo | textos | foto à direita.
- **bioma_piscina:** a piscina ocupa 80% da largura da foto e não cabe atrás do texto no vertical, então o script trocou a faixa
  translúcida do KV por uma pilha sobre o verde da marca.
- **otium_spa:** foto no topo terminando exatamente onde começa a faixa, para a faixa não cobrir a piscina.
- **otium_living:** sofá centrado no recorte, aceitando ampliação de 1,77× no stories (aviso, não reprovação).

## 4. Ciclo do agente

1. Lê `AGENT_BRIEF.md`, a peça-mestra (JSON e PNG), a tabela de formatos e os ativos.
2. Escreve o script e roda.
3. Usa a prévia interna (partes 2 e 6) para ajustar antes de chamar o verificador oficial.
4. Roda `node engine/bench.mjs check` para cada formato e olha o PNG.
5. Se quer melhorar, edita o script e roda de novo (máximo de 3 verificações por formato).
6. Grava o registro em `runs/R01/logs/R2/<peça>.json`.

## 5. Verificações aplicadas

As mesmas de todos os caminhos: conteúdo e texto idênticos, nada inventado, canvas correto, tudo dentro do canvas, texto sem estouro,
corpo mínimo por papel, área segura, fonte/peso/cor do KV, recorte sem distorção, logo inteiro e no tamanho mínimo, sem colisão,
texto sobre foto só com faixa, área protegida visível e contraste WCAG medido no pixel. Aviso: foto ampliada mais de 1,5×.

## 6. Resultado de produção

| Peça | Linhas | E-mail | Post | Card | Stories | Banner | Verif. | Tokens | Tempo |
|---|---|---|---|---|---|---|---|---|---|
| bioma_produto | 369 | ✔ 0,99 | ✔ 0,97 | ✔ 0,90 | ✔ 0,95 | ✔ 0,87 | 9 | 155 mil | 470 s |
| bioma_sustentabilidade | 408 | ✔ 0,86 | ✔ 0,87 | ✔ 0,89 | ✔ 0,89 | ✔ 0,88 | 5 | 132 mil | 323 s |
| bioma_piscina | 381 | ✔ 0,95 | ✔ 0,96 | ✔ 0,99 | ✔ 0,95 | ✔ 0,98 | 11 | 149 mil | 424 s |
| otium_produto | 295 | ✔ 0,99 | ✔ 0,98 | ✔ 0,98 | ✔ 0,96 | ✔ 0,94 | 7 | 130 mil | 254 s |
| otium_spa | 319 | ✔ 1,00 | ✔ 1,00 | ✔ 1,00 | ✔ 1,00 | ✔ 1,00 | 5 | 137 mil | 362 s |
| otium_living | 291 | ✔ 0,95 | ✔ 0,97 | ✔ 0,97 | ✔ 0,95 | ✔ 0,94 | 8 | 127 mil | 254 s |
| **Total** | **2.063** | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | **45/90** | **831 mil** | **~5,7 min/job** |

Números ao lado do ✔: nota suave (0–1). Média 0,95, a mais alta da bancada (R8: 0,89). Pontos mais fracos nas notas suaves:
preenchimento no banner e no stories (0,65–0,78) e quase-alinhamento de bordas na peça de sustentabilidade (0,25–0,5).
Único aviso: ampliação de 1,77× da foto do living no stories.

## 7. Dificuldades relatadas pelos agentes

| Dificuldade | Como o script resolveu |
|---|---|
| A medida do PIL diverge da do Chromium nas quebras de linha | métricas hhea + raqm; larguras "no limite" descartadas; caixa deslocada pelo vazamento do glifo |
| Título quebrando com palavra órfã ("Norte" sozinha no stories) | largura do título fixada entre dois pontos de quebra |
| Foto 16:9 com área protegida larga nos formatos verticais | foto em banda no topo + bloco de texto sobre a cor da marca, em vez de foto sangrada com faixa |
| Legal de 560 caracteres + 3 atributos no banner 970×250 | colunas com largura calculada e legal a 8 px |
| Quase-alinhamento de bordas (títulos e selos de larguras parecidas) | recalibrar larguras e corpos; nem sempre houve saída limpa |
| Foto de baixa resolução (living 1200×520) no stories | sofá centrado, aceitando ampliação de 1,77× |

## 8. Reaproveitamento do código (teste T01)

Cada script foi rodado nas outras 5 peças, trocando só o nome da peça de entrada: 30 cruzamentos.

| Resultado | Cruzamentos |
|---|---|
| Quebrou ao rodar | 28 |
| Rodou e gerou os 5 formatos | 2 (bioma_piscina → bioma_produto; otium_living → otium_produto) |
| Peças geradas que passaram no QA | **0 de 10** |

Por que quebra: o script fixa os `id` dos elementos do job (`selo`, `legal`, `cta`, `lbl_solar`), a tabela de fontes da marca
(`('Cormorant Garamond', 600)`), o nome do ativo da foto e verificações internas próprias daquela peça. **O código é descartável:**
o que se reaproveita entre jobs é o verificador, a tabela de formatos e o formato da IR, não o script.

Consequência para as regras do projeto:
- **I5 (saída editável no InDesign):** atendida, porque a saída é a mesma IR que o exportador do Motor InDesign consome.
- **I6 (segunda marca sem código novo):** **não atendida** pelo script; atendida pelo resto da cadeia (verificador, formatos, exportador).
- **Objeção antiga ao R2** (F4: "20–60 h/mês de conferência"): ela supunha uma pessoa revisando o código a cada job. Aqui ninguém
  revisa código; o verificador revisa a **saída**. O risco que sobra é o que o verificador não mede (seção 10.2).

## 9. Custos e operação

| | Por peça | Por job (5 formatos) |
|---|---|---|
| Tokens | ~27,7 mil | ~138 mil |
| Tempo do agente | ~70 s | 254–470 s (mediana ~5,7 min) |
| Verificações | 1,5 | 7,5 |
| Código novo | ~69 linhas | ~344 linhas |

Comparação com o R8 (mesma bancada):

| | R2 | R8 |
|---|---|---|
| Passa no QA | 30/30 | 25/30 |
| Formatos fechados com 1 só verificação | 19/30 | 3/30 |
| Tokens por job | ~138 mil | ~103 mil |
| Tempo por job | ~5,7 min | ~2,4 min |
| Código novo por job | ~344 linhas | 0 |
| Reprodutível sem IA | não | sim (o plano regera a peça) |

R2 não teve réplica nesta rodada, então a variação entre execuções não foi medida.

## 10. Resultado no júri cego (referência)

### 10.1 Números

- **Aceitas** (QA ok **e** pelo menos 2 dos 3 jurados mandariam ao cliente sem retoque estrutural): **29/30**.
- "Mandaria ao cliente": 96% dos julgamentos (diretor de arte 93%, revisor de marca 97%, cliente 97%).
- Posição no ranking de 8 versões: 1º lugar em 49 de 90 julgamentos, 1º ou 2º em 85 de 90.

### 10.2 A peça reprovada e o que ela mostra

**bioma_produto, card 1080×1080:** os 3 jurados reprovaram — "as duas torres cortadas nas bordas da foto" e "vazio grande na
coluna de texto". O verificador aprovou a peça, porque o limite de área protegida é relativo ao KV (exige
`min(80%, 90% do visível no KV)`). É uma lacuna do QA a corrigir: o recorte das torres nas laterais deveria reprovar.

Também aprovada por 2 a 1 e com ressalva: **bioma_piscina, stories** (o topo do prédio fica sob a interface do stories e a base fica vazia).

## 11. Como reproduzir

```
cd bancada
python3 runs/R01/scripts/R2/bioma_produto.py          # gera os 5 candidatos do job
node engine/bench.mjs check runs/R01/candidates/R2/bioma_produto__card_1080x1080.json
```
Scripts: `runs/R01/scripts/R2/` · registros dos agentes: `runs/R01/logs/R2/` · QA: `runs/R01/checks/R2/` ·
imagens: `runs/R01/renders/R2/` · teste de reaproveitamento: `runs/T01/` (`transfer_run.json`).
