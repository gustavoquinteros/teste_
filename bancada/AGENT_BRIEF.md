# Bancada de desdobramento — instruções para agentes geradores

Você é um braço de um experimento que compara caminhos para automatizar o **desdobramento**
(adaptar uma peça-mestra/KV 16:9 de incorporadora para outros formatos). Outros braços
(motores determinísticos e outros agentes) resolvem as MESMAS peças; um júri cego vai comparar.
Faça o melhor desdobramento que um diretor de arte da agência mandaria ao cliente.

Diretório: `/home/user/teste_/bancada` (rode os comandos a partir dele).

## Entradas
- Peça-mestra (Layout IR): `fixtures/<layout>.json`; imagem dela: `fixtures/renders/<layout>.png` (abra com Read para ver).
- Formatos e regras (margem, área segura, corpo mínimo por papel, logo mínimo): `fixtures/formats.json`
  (ignore a chave `template`, é de outro braço).
- Ativos (tamanho em px e `protected` = área do ativo que precisa aparecer, normalizada x,y,w,h): `assets/assets.json`.
- Formatos-alvo (sempre os 5): `email_600x1200`, `post_1080x1350`, `card_1080x1080`, `stories_1080x1920`, `banner_970x250`.

## Candidato (o que você entrega)
JSON com o mesmo esquema da peça-mestra, em `runs/R01/candidates/<BRACO>/<layout>__<formato>.json`:
```
{"schema_version":"bancada-0.1","layout_id":"<layout>","brand":"<brand>","_format":"<formato>",
 "canvas":{"width":W,"height":H,"background":"<mesma cor>"},
 "elements":[ ...todos os elementos de conteúdo da peça-mestra com o MESMO id... ]}
```
- TEXT: `text` idêntico (não reescreva, não abrevie), mesma `style.font`, `weight`, `color`; pode mudar `size`,
  `line_height`, `align` e a `geometry` (x,y,width,height,z em px do formato). A caixa precisa conter o texto medido.
- IMAGE: mesmo `asset`; `crop` = janela normalizada [x,y,w,h] do ativo. Sem distorção: (w·asset.width)/(h·asset.height)
  deve ser igual a width/height da caixa (±1,5%). Logo: crop [0,0,1,1] sempre, nunca coberto, ≥ largura mínima.
- SHAPE (role DECOR, ex. faixa de legibilidade): pode remover, mover ou criar (id livre). Texto sobre foto só com faixa
  (SHAPE com opacity ≥ 0.7 entre a foto e o texto, cobrindo o texto) ou se a peça-mestra já faz isso.
- Proibido: remover, inventar ou trocar elemento de conteúdo; reescrever texto; mudar fonte/cor/peso.

## Ferramenta de verificação (mesma régua do júri automático)
`node engine/bench.mjs check runs/R01/candidates/<BRACO>/<layout>__<formato>.json`
→ grava o PNG ao lado do JSON e imprime JSON: `eligible`, `hard` (falhas com motivo), `soft` (notas 0–1),
`text_measured` (extensão real de cada texto em px). Abra o PNG com Read para olhar.

**Orçamento igual para todos os braços com IA: no máximo 3 verificações por formato** (15 no total por peça).
Depois da 3ª, entregue o que tiver. Não apague os PNGs.

## Registro obrigatório
Ao final escreva `runs/R01/logs/<BRACO>/<layout>.json`:
`{"arm":"<BRACO>","layout":"<layout>","checks_per_format":{"email_600x1200":n,...},"final_eligible":{...},"notes":"1-3 frases: o que foi difícil"}`

Não altere nada fora de `runs/R01/candidates/<BRACO>/`, `runs/R01/logs/<BRACO>/` e (se o seu braço pedir) `runs/R01/scripts/<BRACO>/`.
Não leia candidatos, logs ou scripts de outros braços. Não edite o motor nem o verificador.
