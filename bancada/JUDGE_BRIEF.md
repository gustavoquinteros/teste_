# Júri cego — desdobramento de KV

Você julga adaptações de uma peça-mestra (KV 16:9 de incorporadora) para 5 formatos. Cada formato tem
8 versões identificadas só por letra (A–H), feitas por caminhos diferentes, em ordem sorteada. Você NÃO sabe
qual caminho fez qual e não deve tentar descobrir.

Diretório: `/home/user/teste_/bancada`. Você só pode ler:
- `fixtures/renders/<layout>.png` (a peça-mestra) e `fixtures/<layout>.json` (textos oficiais, para conferir);
- `runs/R01/blind/<layout>/<formato>/sheet.png` (todas as versões lado a lado) e `.../<letra>.png` (cada versão em tamanho real; abra para conferir detalhes como texto legal, logo, cortes).
Não leia nada mais em `runs/` (nem candidates, checks, logs, renders) nem em `/tmp`. Não rode o verificador.

Para cada um dos 5 formatos (`email_600x1200`, `post_1080x1350`, `card_1080x1080`, `stories_1080x1920`, `banner_970x250`):
1. Ordene TODAS as letras da melhor para a pior (sem empate).
2. Para cada letra responda: "Um designer da agência mandaria isto ao cliente sem retoque estrutural?" (true/false).
   Retoque pequeno (1–2 px, ajuste fino de corpo) não conta; reposicionar blocos, refazer corte da foto, refazer hierarquia conta.
   Falha inviabilizante = false sempre: texto legal ausente/ilegível, logo cortado/distorcido, texto cortado ou fora da área, prédio/piscina mutilado.
3. Uma frase curta por letra com o motivo principal.

Grave `runs/R01/judgments/<PERSONA>/<layout>.json`:
```
{"persona":"<PERSONA>","layout":"<layout>","formats":{
  "email_600x1200":{"ranking":["C","A",...],"ship":{"A":true,...},"reasons":{"A":"...",...}}, ... }}
```
Valide o JSON (python3 -m json.tool). Responda no fim em até 60 palavras: o que separou as melhores das piores.
