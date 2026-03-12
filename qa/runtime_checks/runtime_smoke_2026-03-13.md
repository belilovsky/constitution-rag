# Runtime smoke check — 2026-03-13

## Commands
- python -m app.ask_cli retrieve "свобода слова"
- python -m app.ask_cli "что сказано о свободе слова"

## Observed result
- retrieve mode works
- answer mode works
- retrieval hit: krk_2026_norm_ru, article 23
- answer generated from retrieved norm fragment
- minimal runtime path confirmed:
  user question -> retrieval -> prompt assembly -> LLM -> answer

## Notes
- answer-layer is operational
- release status still NO-GO until top-10 QA run, blocker register, fix plan, retest
