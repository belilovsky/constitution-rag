# DECISION MEMO — TOP-10 COMPARATIVE QA — 2026-03-13

## Scope

Проведён comparative top-10 critical QA run по 4 системам:
- `S1` — colleagues baseline
- `S2` — colleagues + our changes
- `S3` — our version
- `S4` — standard AI reference

Основа оценки:
- единый question set
- единая scoring rubric
- единые blocker rules
- отдельный QA-run file на каждую систему
- единая comparative matrix

## Context

Текущая стадия проекта — prompt / retrieval / answer-layer QA.
Data-layer закрыт.
Retrieval hotfix зафиксирован.
Release status до blocker closure считается `NO-GO`.

## Findings

### What worked

- 
- 
- 

### Main failures observed

- 
- 
- 

### Comparative interpretation

- Система с лучшим общим профилем:
- Система с наименьшим числом blocker’ов:
- Система с лучшим grounded behavior:
- Система с лучшей safe-failure дисциплиной:
- Система с лучшей политической нейтральностью:
- Система с лучшим exact lookup поведением:

## Release decision by system

- `S1`: `GO / CONDITIONAL GO / NO-GO`
- `S2`: `GO / CONDITIONAL GO / NO-GO`
- `S3`: `GO / CONDITIONAL GO / NO-GO`
- `S4`: `reference-only`

## Final decision

- `preferred_base_for_next_cycle`:
- `reason`:
- `required_fixes_before_next_release`:
- `owner`:
- `target_date`:

## Operational next step

- [ ] Update blocker register
- [ ] Write fix plan
- [ ] Execute fixes
- [ ] Run retest
- [ ] Decide whether to proceed to full 30-case hostile run

## Success criterion

Этот memo считается завершённым, если по нему можно понять:
- какая система сейчас сильнее;
- есть ли у неё открытые P0 blocker’ы;
- можно ли её брать как release candidate;
- если нельзя, какую систему брать как fix target.
