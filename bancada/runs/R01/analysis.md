# Rodada R01

300 adaptações verificadas · 0 julgamentos cegos · jurados: 

| Braço | Passa no QA | Júri: nota (0–1) | Júri: enviaria | Aceitável¹ | Bioma QA | OTIUM QA | Tokens/peça | s/peça |
|---|---|---|---|---|---|---|---|---|
| letterbox (piso) | 0/30 | – |  | 0/0 | 0/15 | 0/15 | 0 | 0.012 |
| resize proporcional | 0/30 | – |  | 0/0 | 0/15 | 0/15 | 0 | 0.014 |
| reflow cego (sem semântica) | 7/30 | – |  | 0/0 | 3/15 | 4/15 | 0 | 0.17 |
| template por formato | 25/30 | – |  | 0/0 | 10/15 | 15/15 | 0 | 0.012 |
| R1 motor semântico | 20/30 | – |  | 0/0 | 11/15 | 9/15 | 0 | 0.165 |
| R1 + otimização | 22/30 | – |  | 0/0 | 11/15 | 11/15 | 0 | 0.922 |
| R8 IA escolhe, código posiciona | 25/30 | – |  | 0/0 | 13/15 | 12/15 | 20,530 | 29.0 |
| R3 IA posiciona direto | 30/30 | – |  | 0/0 | 15/15 | 15/15 | 23,798 | 65.9 |
| R2 IA escreve script por job | 30/30 | – |  | 0/0 | 15/15 | 15/15 | 27,689 | 69.6 |
| R8 réplica | 14/15 | – |  | 0/0 | 10/10 | 4/5 | 21,034 | 26.1 |
| R3 réplica | 15/15 | – |  | 0/0 | 10/10 | 5/5 | 23,693 | 51.6 |

¹ Aceitável = passa em todas as verificações duras **e** a maioria dos jurados mandaria ao cliente sem retoque estrutural.

## Confrontos pareados (mesma adaptação)

| Confronto | Vitórias | Empates | Derrotas |
|---|---|---|---|
| R1 x B0 | 0 | 0 | 0 |
| R8 x R1 | 0 | 0 | 0 |
| R8 x R3 | 0 | 0 | 0 |
| R8 x T1 | 0 | 0 | 0 |
| R1opt x R1 | 0 | 0 | 0 |
| R3 x R2 | 0 | 0 | 0 |
| R8 x R2 | 0 | 0 | 0 |
| T1 x R1 | 0 | 0 | 0 |

## Variância entre réplicas

- R8 x R8b: {"adaptacoes": 15, "mesma_elegibilidade": "15/15", "dif_media_nota_suave": 0.022, "mesma_estrategia": "12/15"}
- R3 x R3b: {"adaptacoes": 15, "mesma_elegibilidade": "15/15", "dif_media_nota_suave": 0.036}

## Por formato (elegíveis / % enviaria)

| Braço | email_600x1200 | post_1080x1350 | card_1080x1080 | stories_1080x1920 | banner_970x250 |
|---|---|---|---|---|---|
| A0 | 0/6 ·  | 0/6 ·  | 0/6 ·  | 0/6 ·  | 0/6 ·  |
| A1 | 0/6 ·  | 0/6 ·  | 0/6 ·  | 0/6 ·  | 0/6 ·  |
| B0 | 5/6 ·  | 1/6 ·  | 0/6 ·  | 1/6 ·  | 0/6 ·  |
| T1 | 6/6 ·  | 6/6 ·  | 5/6 ·  | 5/6 ·  | 3/6 ·  |
| R1 | 5/6 ·  | 4/6 ·  | 3/6 ·  | 3/6 ·  | 5/6 ·  |
| R1opt | 5/6 ·  | 4/6 ·  | 4/6 ·  | 4/6 ·  | 5/6 ·  |
| R8 | 6/6 ·  | 4/6 ·  | 6/6 ·  | 3/6 ·  | 6/6 ·  |
| R3 | 6/6 ·  | 6/6 ·  | 6/6 ·  | 6/6 ·  | 6/6 ·  |
| R2 | 6/6 ·  | 6/6 ·  | 6/6 ·  | 6/6 ·  | 6/6 ·  |
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
