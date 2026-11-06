# Rodada R01

300 adaptações verificadas · 720 julgamentos cegos · jurados: cliente, diretor_arte, revisor_marca

| Braço | Passa no QA | Júri: nota (0–1) | Júri: enviaria | Aceitável¹ | Bioma QA | OTIUM QA | Tokens/peça | s/peça |
|---|---|---|---|---|---|---|---|---|
| letterbox (piso) | 0/30 | – |  | 0/0 | 0/15 | 0/15 | 0 | 0.012 |
| resize proporcional | 0/30 | 0.103 | 0% | 0/30 | 0/15 | 0/15 | 0 | 0.014 |
| reflow cego (sem semântica) | 7/30 | 0.335 | 12% | 1/30 | 3/15 | 4/15 | 0 | 0.17 |
| template por formato | 25/30 | 0.276 | 7% | 1/30 | 10/15 | 15/15 | 0 | 0.012 |
| R1 motor semântico | 20/30 | 0.46 | 21% | 7/30 | 11/15 | 9/15 | 0 | 0.165 |
| R1 + otimização | 22/30 | 0.457 | 24% | 9/30 | 11/15 | 11/15 | 0 | 0.922 |
| R8 IA escolhe, código posiciona | 25/30 | 0.581 | 43% | 11/30 | 13/15 | 12/15 | 20,530 | 29.0 |
| R3 IA posiciona direto | 30/30 | 0.873 | 79% | 24/30 | 15/15 | 15/15 | 23,798 | 65.9 |
| R2 IA escreve script por job | 30/30 | 0.914 | 96% | 29/30 | 15/15 | 15/15 | 27,689 | 69.6 |
| R8 réplica | 14/15 | – |  | 0/0 | 10/10 | 4/5 | 21,034 | 26.1 |
| R3 réplica | 15/15 | – |  | 0/0 | 10/10 | 5/5 | 23,693 | 51.6 |

¹ Aceitável = passa em todas as verificações duras **e** a maioria dos jurados mandaria ao cliente sem retoque estrutural.

## Confrontos pareados (mesma adaptação)

| Confronto | Vitórias | Empates | Derrotas |
|---|---|---|---|
| R1 x B0 | 19 | 2 | 9 |
| R8 x R1 | 16 | 3 | 11 |
| R8 x R3 | 3 | 0 | 27 |
| R8 x T1 | 27 | 0 | 3 |
| R1opt x R1 | 15 | 1 | 14 |
| R3 x R2 | 13 | 0 | 17 |
| R8 x R2 | 1 | 0 | 29 |
| T1 x R1 | 8 | 1 | 21 |

## Variância entre réplicas

- R8 x R8b: {"adaptacoes": 15, "mesma_elegibilidade": "15/15", "dif_media_nota_suave": 0.022, "mesma_estrategia": "12/15"}
- R3 x R3b: {"adaptacoes": 15, "mesma_elegibilidade": "15/15", "dif_media_nota_suave": 0.036}

## Por formato (elegíveis / % enviaria)

| Braço | email_600x1200 | post_1080x1350 | card_1080x1080 | stories_1080x1920 | banner_970x250 |
|---|---|---|---|---|---|
| A0 | 0/6 ·  | 0/6 ·  | 0/6 ·  | 0/6 ·  | 0/6 ·  |
| A1 | 0/6 · 0% | 0/6 · 0% | 0/6 · 0% | 0/6 · 0% | 0/6 · 0% |
| B0 | 5/6 · 11% | 1/6 · 17% | 0/6 · 17% | 1/6 · 0% | 0/6 · 17% |
| T1 | 6/6 · 17% | 6/6 · 6% | 5/6 · 0% | 5/6 · 11% | 3/6 · 0% |
| R1 | 5/6 · 6% | 4/6 · 17% | 3/6 · 22% | 3/6 · 22% | 5/6 · 39% |
| R1opt | 5/6 · 17% | 4/6 · 22% | 4/6 · 22% | 4/6 · 22% | 5/6 · 39% |
| R8 | 6/6 · 39% | 4/6 · 61% | 6/6 · 50% | 3/6 · 39% | 6/6 · 28% |
| R3 | 6/6 · 89% | 6/6 · 78% | 6/6 · 56% | 6/6 · 83% | 6/6 · 89% |
| R2 | 6/6 · 100% | 6/6 · 100% | 6/6 · 83% | 6/6 · 94% | 6/6 · 100% |
| R8b | 3/6 ·  | 3/6 ·  | 3/6 ·  | 2/6 ·  | 3/6 ·  |
| R3b | 3/6 ·  | 3/6 ·  | 3/6 ·  | 3/6 ·  | 3/6 ·  |

## Falhas duras mais comuns

- **A0**: {'corpo_minimo': 95, 'logo_tamanho_minimo': 12, 'area_segura': 11, 'logo_na_area_segura': 6}
- **A1**: {'corpo_minimo': 95, 'area_protegida_visivel': 23, 'area_segura': 13, 'logo_tamanho_minimo': 12}
- **B0**: {'corpo_minimo': 32, 'logo_tamanho_minimo': 8, 'area_protegida_visivel': 7, 'area_segura': 2}
- **T1**: {'area_segura': 8, 'texto_sobre_logo_ou_icone': 4, 'dentro_do_canvas': 3, 'texto_sobre_texto': 3}
- **R1**: {'area_protegida_visivel': 4, 'area_segura': 4, 'contraste': 3}
- **R1opt**: {'area_protegida_visivel': 4, 'contraste': 3, 'area_segura': 1}
- **R8**: {'area_segura': 3, 'area_protegida_visivel': 2}
- **R8b**: {'area_segura': 1}
