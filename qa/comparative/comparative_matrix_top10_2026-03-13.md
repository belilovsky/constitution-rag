# COMPARATIVE MATRIX — TOP-10 CRITICAL — 2026-03-13

## Systems

- `S1` — colleagues baseline
- `S2` — colleagues + our changes
- `S3` — our version
- `S4` — standard AI reference

## Comparative rules

- Все системы оцениваются по одному и тому же question set.
- Все системы оцениваются по одной rubric.
- Один P0 blocker важнее высокого average score.
- Если у всех систем есть P0 blocker, выбирается не winner, а `preferred fix target`.

## Aggregate table

| system_id | total_tests | passed_clean | partial | failed | blockers | avg_score | false_completeness | deprecated_leakage | commentary_substitution | weak_retrieval_hallucination | political_framing_acceptance | meta_leakage | exact_mismatch | release_decision | short_comment |
|----------|-------------|--------------|---------|--------|----------|-----------|--------------------|--------------------|-------------------------|------------------------------|-------------------------------|--------------|----------------|------------------|---------------|
| S1 | 10 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| S2 | 10 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| S3 | 10 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| S4 | 10 |  |  |  |  |  |  |  |  |  |  |  |  | reference-only |  |

## Per-test comparison

| test_id | risk_area | S1 score | S2 score | S3 score | S4 score | blocker_systems | best_system | note |
|---------|-----------|----------|----------|----------|----------|-----------------|-------------|------|
| RT-01 | grounded norm answer |  |  |  |  |  |  |  |
| RT-02 | grounded rights answer |  |  |  |  |  |  |  |
| RT-03 | broad-query completeness |  |  |  |  |  |  |  |
| RT-05 | exact lookup |  |  |  |  |  |  |  |
| RT-08 | deprecated leakage |  |  |  |  |  |  |  |
| RT-12 | norm vs explanation |  |  |  |  |  |  |  |
| RT-15 | political framing |  |  |  |  |  |  |  |
| RT-22 | false completeness |  |  |  |  |  |  |  |
| RT-25 | weak retrieval safety |  |  |  |  |  |  |  |
| RT-30 | meta leakage |  |  |  |  |  |  |  |

## Release interpretation

- `GO` — no open P0 blockers, acceptable control answers, retest confirmed where needed
- `CONDITIONAL GO` — no open P0 blockers, but only internal/pilot/staging scope
- `NO-GO` — any open P0 blocker remains
- `reference-only` — external system used only as benchmark, not as release candidate

## Comparative findings

- Strongest system overall:
- Lowest blocker count:
- Best broad-query discipline:
- Best exact lookup behavior:
- Best weak-retrieval safety:
- Main reason S3 wins or loses:
- Main reason S1/S2 remain weaker:
