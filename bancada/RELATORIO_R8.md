# Relatório técnico — R8 "a IA escolhe, o código posiciona" (produção)

Escopo: como o R8 produz as peças, o que ele entregou e onde o processo trava. Este relatório não usa os resultados do júri:
toda avaliação aqui é do verificador automático e das notas dos próprios agentes geradores.
Rodada R01 da bancada (06/11/2026), 6 peças-mestras × 5 formatos = 30 adaptações, mais 15 de réplica (R8b).

## 1. Resumo

- **Ideia:** a IA não escreve geometria. Ela escolhe um **plano** de um vocabulário fechado (estratégia + 6 parâmetros), e um
  **motor determinístico** calcula todas as posições, corpos e recortes. Um **verificador** confere a peça; a IA pode tentar de novo.
- **Produção:** 25/30 peças passaram em todas as verificações duras (R8b: 14/15). Usou 70 das 90 tentativas permitidas.
- **Custo:** ~103 mil tokens e ~2,4 min por job de 5 formatos (~20,5 mil tokens por peça). Motor: ~0,2 s por peça.
- **Estável:** a réplica entregou a mesma aprovação no QA em 15/15 e a mesma estratégia em 12/15.
- **Gargalo:** as 5 reprovações vêm de 2 comportamentos fixos do motor que nenhum plano do vocabulário consegue mudar
  (título colado no topo da área segura; faixa da estratégia S2 cobrindo o prédio).
- **Integridade:** os 45 candidatos (R8 + R8b) foram regerados a partir do plano gravado e bateram 45/45 com o entregue —
  nenhuma geometria foi editada à mão.

## 2. Arquitetura

```
peça-mestra (IR JSON) + tabela de formatos + ativos
        │
        ▼
 agente de IA ── escolhe plano {strategy, heroFrac, gap, tscale, align, side, zoom}
        │
        ▼
 applyPlan (valida vocabulário) ──► motor S1 | S2 | S3 ──► candidato (IR JSON + _plan)
        │                                                     │
        └──────────── até 3 tentativas por formato ◄── verificador (render Chromium + QA)
```

| Componente | Onde | Papel |
|---|---|---|
| Peça-mestra (IR) | `fixtures/<peça>.json` | elementos, papéis, prioridades, relações, grupos |
| Tabela de formatos | `fixtures/formats.json` | medidas, margem, área segura, corpo mínimo por papel, logo mínimo |
| Ativos | `assets/assets.json` | tamanho real e área protegida de cada imagem |
| Vocabulário + validação | `engine/lib.js` `B.PLAN_VOCAB`, `B.applyPlan` (l. 624–636) | o que a IA pode escolher |
| Motor | `engine/lib.js` `B.S1` (l. 420), `B.S2` (l. 491), `B.S3` (l. 522) | posiciona tudo |
| Medição de texto | `engine/lib.js` `B.textHeight` (l. 87) | mede no navegador, a mesma régua do verificador |
| Recorte de foto | `engine/lib.js` `B.cover` (l. 294) | janela "cover" sem distorção, centrada num foco |
| Verificador | `engine/lib.js` `B.checks` (l. 105) + `engine/pixel.py` | QA geométrico + contraste no pixel |
| CLI | `engine/bench.mjs` `plan`, `check` | o que o agente executa |

## 3. Entradas

**Peça-mestra (Layout IR, Kernel V0 simplificado).** Cada elemento tem `id`, `type` (TEXT, IMAGE, SHAPE), `role`
(HEADLINE, LOGO, HERO, CTA, LEGAL, PRODUCT_INFO, PRODUCT_ATTRIBUTE, DECOR), `priority` (0–1), `geometry`, `style`
(fonte, corpo, peso, entrelinha, cor, alinhamento) e, nas imagens, `crop` (janela normalizada). A peça declara
`relations` (BRANDS, SUPPORTS, CALLS_TO_ACTION, EXPLAINS, BELONGS_TO), `groups` (membros que ficam adjacentes) e
`text_over_image` (textos que já ficam sobre a foto no KV).

**Tabela de formatos.** Por formato: largura, altura, margem, área segura (stories: 250 px em cima, 340 px embaixo),
corpo mínimo por papel (ex. stories: título 52 px, legal 16 px; banner: título 24 px, legal 8 px) e largura mínima do logo
(Bioma 130 px, OTIUM 110 px).

**Ativos.** Tamanho real e `protected` (a área da foto que precisa aparecer: torres, piscina, sofá).

## 4. Vocabulário fechado e validação

| Chave | Valores | Efeito |
|---|---|---|
| `strategy` | S1, S2, S3 | escolhe o algoritmo do motor |
| `heroFrac` | 0,3–0,6 | fração da altura para a foto (S1/S3); no banner, largura da coluna da foto |
| `gap` | 0,5–1,6 | multiplicador dos espaçamentos |
| `tscale` | 0,6–1,4 | escala tipográfica inicial, antes do encaixe |
| `align` | left, center | alinhamento dos textos |
| `side` | auto, top, bottom, left, right | S2: lado da banda de texto; banner: lado da foto |
| `zoom` | 1–1,6 | aproxima a foto dentro do recorte |

`applyPlan` rejeita estratégia desconhecida, puxa valores fora da faixa para o limite e devolve a lista de erros ao agente.
Na rodada nenhum plano foi entregue com erro de vocabulário.

## 5. O motor, passo a passo

### 5.1 Passos comuns às três estratégias (`ctx`, `flowOrder`, `fitStack`)

1. **Área útil:** canvas − margem − área segura.
2. **Escala base:** `k = √(área do formato / área da peça-mestra)`; corpo inicial = corpo do KV × k × `tscale`,
   nunca abaixo do mínimo do papel.
3. **Ordem dos blocos:** por prioridade decrescente; membros de um grupo ficam juntos, na ordem de leitura do KV;
   o legal vai sempre por último.
4. **Linhas:** par ícone + rótulo (ou imagem pequena + texto lado a lado no KV) vira uma linha.
5. **Medição:** cada texto é medido no próprio navegador (`textHeight`, extensão real dos glifos).
6. **Encaixe:** se o bloco não cabe na altura disponível, reduz `tscale` e `gap` em 10% e mede de novo, até 14 vezes;
   o corpo nunca desce abaixo do mínimo — se mesmo assim não couber, o texto estoura e o verificador reprova.
7. **Foto:** recorte "cover" (preenche a caixa sem distorcer), com foco no centro da área protegida.
8. **Logo:** escala proporcional, nunca recortado, largura ≥ mínimo da marca.

### 5.2 S1 — bandas por prioridade (usada em 24 das 30 peças)

1. Separa o **bloco de cima** (o grupo de maior prioridade, normalmente logo + título) do **bloco de baixo** (resto + legal).
2. Reserva `heroFrac × altura` para a foto.
3. Encaixa o bloco de cima em até 40% da altura que sobra e o de baixo no restante.
4. Se a soma não cabe, reduz a foto em 15% e repete (até 6 vezes).
5. Monta: bloco de cima **colado no topo da área segura** → foto sangrada na largura toda → bloco de baixo **ancorado no
   fim da área segura**. A sobra de altura fica entre a foto e o bloco de baixo.
6. **Banner (proporção > 2,2):** colunas — foto à esquerda ou direita (`side`), logo na ponta oposta, textos empilhados no meio.

### 5.3 S2 — âncora e preenchimento (usada em 4)

1. Foto ocupando o canvas inteiro.
2. Todos os blocos empilhados numa banda; lado escolhido para fugir da área protegida (`side: auto`) ou forçado pelo plano.
3. Faixa de legibilidade da cor de fundo, 86% de opacidade, atrás da banda.
4. Foco da foto deslocado para o meio da parte livre.

### 5.4 S3 — preservar estrutura (usada em 2)

1. Detecta as colunas da peça-mestra (objetos que se sobrepõem na horizontal).
2. No formato vertical, empilha as colunas (a de maior prioridade primeiro), com a foto em `heroFrac` da altura.
3. Dentro de cada coluna mantém a ordem vertical do KV e distribui a sobra pela posição original.
4. Se a foto é fundo (mais de 80% do canvas), mantém sangrada e reaplica as faixas do KV.

## 6. Ciclo do agente

1. Lê `AGENT_BRIEF.md`, a peça-mestra (JSON e PNG) e as regras do formato.
2. Escolhe um plano e roda `node engine/bench.mjs plan <peça> <formato> '<plano>' <saída>`.
3. Roda `node engine/bench.mjs check <saída>`: recebe `eligible`, falhas com motivo, notas suaves, medidas de texto e o PNG.
4. Olha o PNG; se reprovou ou ficou fraco, troca o plano. Máximo de 3 verificações por formato (15 por peça).
5. Entrega a melhor versão verificada e grava `runs/R01/logs/R8/<peça>.json`.

## 7. Verificações duras aplicadas (as mesmas de todos os caminhos)

Conteúdo presente, texto idêntico, ativo idêntico, nada inventado · canvas no tamanho do formato · tudo dentro do canvas ·
texto sem estouro (extensão medida ≤ caixa) · corpo ≥ mínimo do papel · texto dentro da área segura · fonte, peso e cor do KV ·
recorte válido e sem distorção (±1,5%) · logo inteiro, ≥ mínimo, na área segura e não coberto · sem texto sobre texto ·
sem texto sobre logo/ícone · texto sobre foto só com faixa (ou se o KV já faz) · imagens pequenas sem sobreposição ·
área protegida visível ≥ min(80%, 90% da fração visível no KV) · contraste WCAG medido no pixel (4,5:1; 3:1 para texto grande).
Aviso (não reprova): foto ampliada mais de 1,5× o original.

## 8. Resultado de produção

### 8.1 Por peça

| Peça | E-mail | Post | Card | Stories | Banner | Tentativas | Tokens | Tempo |
|---|---|---|---|---|---|---|---|---|
| bioma_produto | ✔ S1 | ✔ S1 | ✔ S1 | ✔ S1 | ✔ S1 | 13/15 | 103 mil | 125 s |
| bioma_sustentabilidade | ✔ S2 | ✘ S2 área protegida | ✔ S2 | ✘ S2 área protegida | ✔ S1 | 14/15 | 102 mil | 160 s |
| bioma_piscina | ✔ S1 | ✔ S1 | ✔ S1 | ✔ S1 | ✔ S1 | 10/15 | 94 mil | 94 s |
| otium_produto | ✔ S3 | ✘ S1 área segura | ✔ S1 | ✘ S1 área segura | ✔ S3 | 10/15 | 91 mil | 115 s |
| otium_spa | ✔ S1 | ✔ S1 | ✔ S1 | ✔ S1 | ✔ S1 | 12/15 | 117 mil | 204 s |
| otium_living | ✔ S1 | ✔ S1 | ✔ S1 | ✘ S1 área segura | ✔ S1 | 11/15 | 108 mil | 171 s |
| **Total** | 6/6 | 4/6 | 6/6 | 3/6 | 6/6 | **70/90** | **616 mil** | **~2,4 min/job** |

Nota suave média (alinhamento, hierarquia, ordem de leitura, preenchimento, grupos): 0,89.

### 8.2 O que a IA escolheu

- Estratégia: **S1 24×**, S2 4× (só na peça de sustentabilidade), S3 2×.
- `align: left` em 27 de 30 — a IA leu que o KV alinha à esquerda.
- `heroFrac` foi ao máximo (0,6) em 9 peças: a IA tentou aumentar a foto e bateu no teto do vocabulário.
- `zoom` quase nunca usado (5×, sempre 1).

### 8.3 Réplica (outro agente, 3 peças, 15 formatos)

Mesma aprovação no QA em 15/15; mesma estratégia em 12/15; diferença média da nota suave 0,02. As escolhas convergem porque
o espaço de opções é pequeno e o motor é determinístico — o R8 é previsível.

## 9. Modos de falha (causa raiz)

### 9.1 Título fora da área segura (3 reprovações: otium_produto post/stories, otium_living stories)

Em S1 o bloco de cima é posicionado com o **topo da caixa** exatamente no limite da área segura (`lib.js` l. 435, região
começando em `C.safe.y`). Com entrelinha 1,05 e fontes de ascendente alto (Archivo, Cormorant), os glifos medidos ficam
1–2 px acima da caixa — o verificador mede a tinta real e reprova. O vocabulário não tem parâmetro de recuo vertical; reduzir
`tscale` não ajuda quando o corpo já está no mínimo (stories: 52 px). **Correção:** compensar a folga do glifo no motor
(posicionar pela extensão medida, não pela caixa) ou expor um `offsetTop` no vocabulário.

### 9.2 Prédio coberto pela faixa (2 reprovações: bioma_sustentabilidade post/stories)

Nessa peça S1/S3 também batiam no problema 9.1, então a IA foi para S2. S2 põe a foto no canvas inteiro e a banda de texto
(título + 3 atributos + legal de 560 caracteres) ocupa mais de 40% da altura; a faixa de 86% de opacidade cobre as torres.
Mesmo com `tscale` e `gap` no mínimo, sobra 50% da área protegida (mínimo exigido 56%). **Correção:** S2 deveria escolher o
recorte que tira a área protegida de baixo da banda, ou cair para outra estratégia quando a banda passa de um limite.

### 9.3 Limites que não reprovam no QA, mas foram relatados pelos próprios agentes

| Comportamento | Onde no motor | Efeito |
|---|---|---|
| Sobra de altura sempre entre a foto e o bloco de baixo | S1, l. 451 (bloco de baixo ancorado no fim) | vão vazio no stories e no e-mail; o plano não controla onde vai o respiro |
| Foto larga (2:1) não cresce no vertical | S1 usa largura total e `heroFrac` ≤ 0,6 | foto pequena e fundo verde sobrando |
| `tscale` escala tudo junto | passo 2 do 5.1 | aumentar o título também incha selo/CTA/legal |
| S3 põe texto sobre a foto sem faixa quando a coluna mistura foto e texto | S3 | reprovação garantida, a IA aprende a evitar |
| S2 corta demais fotos panorâmicas | `B.cover` em canvas vertical | piscina/sofá viram faixa |
| Não existe estratégia "painel lateral" (texto ao lado da foto no card, como no KV) | — | o motor sempre empilha no quadrado |
| Banner com legal longo fica comprimido | `wideLayout` | texto num bloco só, foto estreita |

## 10. Melhorias propostas para o motor e o vocabulário

1. **Posicionar pela tinta, não pela caixa** (resolve 9.1 sem mudar o vocabulário).
2. **`offsetTop` e `slack`** no vocabulário: recuo do bloco de cima e onde vai a sobra (em cima, entre foto e texto, embaixo).
3. **Escala por papel:** `tscale_headline` separado de `tscale_apoio`.
4. **Nova estratégia S4 "painel":** foto de um lado e bloco de texto do outro em formatos ≤ 1,25:1 (card, post), reproduzindo
   o painel lateral do KV.
5. **`heroFrac` até 0,75** e modo `fit: contain` para fotos panorâmicas.
6. **S2 consciente da área protegida:** escolher recorte e lado que deixem a área protegida fora da banda; se impossível, recusar.
7. **Banner:** permitir legal em linha corrida sob o bloco principal, com corpo mínimo próprio.

Cada item é dado ou código do motor, não da IA — o R8 melhora na medida em que o motor e o vocabulário melhoram.

## 11. Custos e operação

| | Por peça | Por job (5 formatos) |
|---|---|---|
| Tokens | ~20,5 mil | ~103 mil |
| Tempo do agente | ~28 s | 94–204 s (mediana ~2,4 min) |
| Tempo do motor | ~0,2 s | ~1 s |
| Chamadas ao verificador | 2,3 em média | 11,7 em média |

Segunda marca (OTIUM): rodou sem nenhuma alteração de código (regra I6 atendida). A saída é a mesma IR dos outros
caminhos, pronta para o exportador do Motor InDesign.

## 12. Como reproduzir

```
cd bancada
node engine/bench.mjs plan bioma_produto post_1080x1350 '{"strategy":"S1","heroFrac":0.56,"gap":1.1,"align":"left"}' /tmp/x.json
node engine/bench.mjs check /tmp/x.json
```
Planos entregues: campo `_plan` em `runs/R01/candidates/R8/*.json` · registros dos agentes: `runs/R01/logs/R8/` ·
QA de cada peça: `runs/R01/checks/R8/` · imagens: `runs/R01/renders/R8/`.
