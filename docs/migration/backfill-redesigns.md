# Backfill dos redesenhos (T12)

Script: [`scripts/backfill_redesigns.py`](../../scripts/backfill_redesigns.py)
(`python scripts/backfill_redesigns.py [--dry-run] [--json]`).

O backfill preserva os identificadores das tabelas legadas, então o mapeamento é
direto e a reexecução não duplica dados (`INSERT OR IGNORE` + chaves naturais).

## Ordem e mapeamento

| Etapa | Origem | Destino | Regra |
| --- | --- | --- | --- |
| 1 | `planning.campaign_id` + `brand_id` | `campaigns.brand_id` | encerrado na T25: a migração `0018` preenche e torna a coluna NOT NULL; o script não escreve mais nela |
| 2 | `planning` | `content_plans` | `briefing = planning_info`; datas convertidas com `date()`; pula plano cujo campaign/persona não pertence à marca |
| 3 | `planning_*_amount` | `content_plan_items` | `IMAGE`/`CAROUSEL`/`STORIES`, somente quantidades > 0 |
| 4 | `planning_special_dates` | `content_plan_special_dates` | data válida; `label = 'legacy'` para a unicidade funcionar |
| 5 | `post_structure` | `posts` | `publication_status = DRAFT`, `approval_status = PENDING` (o legado não distinguia) |
| 6 | `post_structure` | `post_designs` | `format`/`ratio` validados contra os enums; `STORIES` só com `RATIO_9_16` |
| 7 | `design_structure` | `post_designs` | herda `format`/`ratio` do `post_structure` pai |
| 8 | `design_structure` | `design_slides` | `position = 0`; `headline`/`cta`/`art_guiding` do post |
| 9 | `generated_image` | `generated_images` | `SUCCEEDED` só com URL, tamanho e resolução `WxH`; caso contrário `FAILED` com `error_message`; `is_current = false` |

## Invariantes

- `content_plans` só é criado quando `campaigns.brand_id = planning.brand_id` **e**
  `personas.brand_id = planning.brand_id`; o resto é pulado e contado no relatório.
- `posts` só existe com `content_plans` correspondente; `post_designs` com `posts`;
  `design_slides` com `post_designs`; `generated_images` com `design_slides`.
- Nenhuma linha viola os CHECKs do modelo final: imagem legada incompleta vira
  `FAILED` com mensagem, e não `SUCCEEDED` sem arquivo.
- Duas execuções seguidas reportam zero linhas na segunda.

## Relatório

O script imprime as contagens por etapa (`--json` para máquina). As linhas puladas
aparecem como diferença entre a origem e o destino; `dry_run` executa tudo dentro
da transação e faz rollback.
