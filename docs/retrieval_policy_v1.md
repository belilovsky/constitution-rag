# RETRIEVAL POLICY ДЛЯ CONSTITUTION-RAG

Настоящий документ является частью prompt / retrieval / answer слоя проекта `constitution-rag` и должен применяться совместно с актуальной канонической системной инструкцией chatbot-layer.

Если между удобством retrieval, score-based ranking, скоростью ответа и source-priority возникает конфликт, приоритет всегда имеют:
1. корректный слой источника;
2. защита от ложной актуализации;
3. сохранение значимых метаданных;
4. безопасная передача контекста в answer-layer.

Цель этой политики — не просто находить похожие фрагменты, а передавать модели такие материалы, которые позволяют дать grounded-ответ без:
- подмены `norm`-слоя разъяснительными материалами;
- ложной полноты на широких вопросах;
- утраты project / transition / deprecated-статуса;
- смешения исторического и основного слоя;
- подмены точного запроса соседней нормой;
- провоцирования answer-layer на галлюцинацию.

---

## 1. НАЗНАЧЕНИЕ

Эта политика определяет:
- какие document layers считаются приоритетными;
- как маршрутизировать разные типы запросов;
- какие retrieval paths использовать для exact, broad, mixed и comparison запросов;
- как отбирать, ранжировать и собирать фрагменты;
- как сохранять статус, происхождение и структурный контекст;
- как не допускать `1995 deprecated` leakage;
- как не допускать `commentary` / `faq` substitution вместо `norm`;
- как снижать риск false completeness;
- какие минимальные требования действуют перед передачей контекста в answer-layer.

Retrieval-policy нужна для того, чтобы answer-layer получал не просто релевантный текст, а **безопасный и интерпретируемый контекст**.

---

## 2. ПРОЕКТНЫЙ КОНТЕКСТ

`constitution-rag` — это не просто ingestion или ETL-репозиторий.

В этом проекте:
- raw files;
- normalization;
- import в PostgreSQL;
- retrieval routing

являются подготовительным слоем для grounded chatbot answers.

На текущем этапе:
- data-layer на момент составления данной политики считался завершённым; при добавлении новых наборов данных настоящая политика подлежит обязательному обновлению;
- retrieval-layer находится в рабочем состоянии после hotfix;
- текущий release gate находится на уровне prompt / retrieval / answer-layer QA.

Следовательно, retrieval-policy должна оцениваться не только по метрике «нашёл похожий кусок», а по тому, помогает ли она answer-layer:
- держать source-priority;
- не обещать полноту;
- не смешивать `2026` и `1995`;
- не заменять `norm` commentary-слоем;
- безопасно вести себя при weak retrieval;
- не принимать политический framing как факт.

---

## 3. ИСХОДНЫЕ НАБОРЫ ДАННЫХ

Система работает с пятнадцатью документными наборами:

Norm-layer (основной нормативный слой):
- `krk_2026_norm_ru`
- `krk_2026_norm_kz`

Commentary-layer (основной разъяснительный слой):
- `krk_2026_commentary_ru`
- `krk_2026_commentary_kz`

Civic-education sub-layer (гражданское просвещение — вторичный, только как supporting context):
- `krk_2026_ce_theses_ru` — ключевые аспекты + тезисы комиссии
- `krk_2026_ce_audiences_ru` — линии для целевых аудиторий

FAQ-layer (пользовательские пояснения):
- `krk_2026_faq_ru` — краткий FAQ из PDF-брошюры
- `krk_2026_faq_kz`
- `krk_2026_faq_extra_ru` — расширенный FAQ с constitution.my
- `krk_2026_faq_extra_kz`
- `krk_2026_faq_extra_en` — расширенный FAQ (английский язык)

Comparison-only (только для comparison-mode запросов):
- `krk_2026_ce_comparison_ru` — таблица сравнения 1995 ↔ 2026

Historical/deprecated-layer:
- `krk_1995_deprecated_ru`
- `krk_1995_deprecated_kz`

Restricted (не для ordinary user retrieval — требует отдельного решения):
- `krk_2026_ce_lines_ru` — референдумные линии + контраргументы

Смысл слоёв:
- `2026 norm` — основной norm-layer проекта;
- `2026 commentary` — дополнительный разъяснительный слой;
- `2026 civic-education` — вторичный commentary-sub-layer (не равен основному commentary);
- `2026 faq` — упрощённый пояснительный слой (расширенный FAQ имеет приоритет над кратким при конфликте);
- `comparison-table` — структурированная таблица сравнения, только для comparison-mode;
- `1995 deprecated` — historical/deprecated слой только для сравнения, исторической справки или прямого historical-запроса;
- `restricted` — не участвует в ordinary retrieval без отдельного решения.

Критическое правило:
- `1995 deprecated` не должен использоваться как текущая норма по умолчанию.

Если backend хранит дополнительные служебные поля, это допустимо, но они не должны ломать:
- layer priority;
- language priority;
- deprecated handling;
- status labeling;
- structural precision;
- source labeling.

---

## 4. ГЛАВНЫЙ ПРИНЦИП RETRIEVAL

Retrieval должен подбирать не «вообще релевантные» куски текста, а **наиболее приоритетные и безопасные для ответа фрагменты**.

Главное правило:
- сначала искать подтверждение в `2026 norm`;
- затем, при необходимости, добавлять `2026 commentary`;
- затем, при необходимости, добавлять `2026 faq`;
- `1995 deprecated` использовать только по отдельному основанию.

Retrieval не должен оптимизироваться только на lexical similarity.

Retrieval не должен оптимизироваться только на semantic similarity.

Для юридических и конституционных материалов retrieval обязан учитывать одновременно:
- layer;
- dataset;
- language;
- status;
- deprecated-признак;
- article / point / структурный reference;
- query type;
- полноту покрытия;
- риск смешения слоёв;
- риск ложной полноты;
- риск article mismatch;
- риск context truncation.

Для этого простого similarity score недостаточно без маршрутизации, фильтрации, структурной проверки и metadata-aware ranking.

---

## 5. ПРИОРИТЕТ ИСТОЧНИКОВ

Базовый порядок приоритета в ordinary mode:

1. `2026 norm` (`krk_2026_norm_ru / kz`)
2. `2026 commentary` — основной разъяснительный слой (`krk_2026_commentary_ru / kz`)
2b. civic-education sub-layer — только как вторичный supporting context, не равен основному commentary
    (`ce_theses_ru`, `ce_audiences_ru`)
3. `faq` — расширенный имеет приоритет над кратким при конфликте:
    3a. `faq_extra_ru / faq_extra_kz / faq_extra_en` (constitution.my — приоритет)
    3b. `krk_2026_faq_ru / kz` (PDF-брошюра — вторичный)
4. `1995 deprecated` — только по отдельному основанию
4b. `ce_comparison_ru` — только в comparison-mode; запрещён в ordinary mode

Restricted — не участвует в ordinary retrieval:
- `ce_lines_ru`

Это правило сильнее простой текстовой близости, если два фрагмента близки по теме.

Следствия:
- `2026 norm` должен побеждать `2026 commentary`, если оба отвечают на один и тот же вопрос;
- `2026 commentary` не должен вытеснять релевантный `2026 norm`;
- `2026 faq` не должен быть основным источником, если по теме найден `norm`;
- `1995 deprecated` не должен попадать в верх ordinary-ответа, если доступен релевантный `2026 norm`;
- semantic proximity не должна побеждать правильный layer priority;
- commentary и faq допустимы только как supporting context после найденного norm.

Source-priority важнее, чем сходство формулировок.

---

## 6. ПОВЕДЕНИЕ ПО УМОЛЧАНИЮ

Если пользователь задаёт обычный вопрос без уточнения периода, редакции, слоя или режима сравнения:
- сначала искать в `2026 norm`;
- не подмешивать `1995 deprecated` без отдельного основания;
- `commentary` и `faq` добавлять только как вторичный supporting context;
- historical/deprecated слой не выводить в основную линию ответа по умолчанию.

Если пользователь прямо просит:
- сравнение — разрешается retrieval из `2026 norm` и `1995 deprecated`;
  При сравнительных запросах типа «чем отличается 2026 от 1995» также разрешается (и предпочтительно) использование `ce_comparison_ru` как первого шага поиска.
  `ce_comparison_ru` является структурированной таблицей сравнения и должен передаваться в answer-layer с явной маркировкой `layer=comparison-table`.
  `ce_comparison_ru` не используется в ordinary mode (без comparison-запроса);
- historical query — разрешается retrieval из `1995 deprecated`;
- объяснение простыми словами — разрешается добавить `commentary` и / или `faq`, но только после поиска по `norm`;
- разъяснение — разрешается retrieval из `commentary`, но `norm` всё равно ищется первым;
- точную статью или пункт — сначала использовать exact / lexical path внутри релевантного слоя;
- перечисление по широкой теме — retrieval должен расширять охват, а не давать узкий случайный top-k.

По умолчанию retrieval не должен расширять ordinary query на deprecated-слой только потому, что deprecated chunk даёт высокий similarity score.

---

## 7. ПРАВИЛО ДЛЯ 1995 DEPRECATED

Слой `1995 deprecated` допустим только в четырёх случаях:

1. пользователь прямо спрашивает о Конституции 1995 года;
2. пользователь прямо просит сравнение `1995 ↔ 2026`;
3. пользователю нужен historical context, и это отдельно маркируется;
4. в answer-layer нужно показать контролируемое сравнение найденных норм с явным разведением слоёв.

Во всех остальных случаях retrieval не должен поднимать `1995 deprecated` в верх ordinary-выдачи, если найден релевантный `2026 norm`.

Если в retrieved output присутствует `1995 deprecated`, он должен быть:
- явно маркирован;
- логически отделён от `2026`;
- запрещён к слиянию с `2026 norm` в единое утверждение без comparison mode;
- передан с `deprecated`-меткой как обязательным защитным сигналом.

Критический риск:
если deprecated-статус теряется, answer-layer начнёт цитировать 1995 как текущую норму.

Поэтому:
- soft penalty недостаточен;
- ordinary mode должен использовать hard filtering или функционально эквивалентный metadata-aware routing;
- `1995 deprecated` leakage в ordinary mode считается blocker-классом ошибки.

---

## 8. ПРАВИЛО ДЛЯ 2026 PROJECT STATUS

Слой `2026` является основным norm-layer проекта, но его фактический правовой статус не должен автоматически трактоваться retrieval-слоем как окончательно действующий без подтверждения.

Retrieval обязан сохранять и передавать признаки статуса, если они присутствуют:
- `project`;
- `draft`;
- `temporary`;
- `transition`;
- `effective_date`;
- `entry_into_force`;
- переходные положения;
- указание на временный, условный или проектный характер текста;
- признаки replacement / continuation / repeal, если они прямо есть в данных.

Если по найденному фрагменту или метаданным видно, что норма имеет проектный, переходный или условный статус, retrieval не должен терять этот сигнал.

Если таких сигналов нет:
- retrieval может маркировать слой как `2026 norm`;
- но не должен сам делать вывод «это окончательно действующее право».

Retrieval не выводит юридический статус сверх текста и метаданных.

---

## 9. ЯЗЫКОВАЯ ПОЛИТИКА

Retrieval сначала должен пытаться искать ответ на языке запроса пользователя.

Приоритет языка:
- вопрос на русском → сначала `*_ru`;
- вопрос на казахском → сначала `*_kz`.

Вопрос на английском языке:
- сначала искать в `faq_extra_en` (единственный англоязычный набор);
- если `faq_extra_en` не даёт достаточного norm-подтверждения, использовать controlled cross-language fallback на `*_ru` norm, с явной маркировкой, что нормативная основа взята из русскоязычного слоя;
- английский ответ не должен подменять русский/казахский norm-layer собственным содержанием `faq_extra_en` без нормативной основы.

Если запрос смешанный:
- определить доминирующий язык;
- сначала искать в соответствующем языке слоя;
- второй язык использовать только как controlled fallback.

Кросс-языковой fallback допустим, если:
- на языке запроса нет достаточного `norm`-фрагмента;
- на другом языке найден более точный norm;
- fallback-фрагмент явно маркируется;
- fallback не подменяет нормальный поиск на языке пользователя.

Нельзя:
- смешивать RU и KZ фрагменты без необходимости;
- использовать cross-language retrieval как shortcut вместо основного поиска;
- отдавать предпочтение `commentary` на языке вопроса перед более точным `norm` на другом языке без явного основания;
- собирать из разных языков один псевдоцитатный блок без уверенности, что это одна и та же норма.

Если найден релевантный `norm` на другом языке, он предпочтительнее слабого или косвенного `commentary` на языке запроса.

---

## 10. КЛАССИФИКАЦИЯ ЗАПРОСОВ

Перед основным поиском запрос должен быть классифицирован по типу.

Минимальные категории:
- ordinary current-layer query;
- broad topical query;
- exact article lookup;
- exact point / subpoint lookup;
- structural follow-up query;
- comparison query;
- historical / 1995 query;
- simple explanation query;
- existence query;
- mixed-topic query;
- weak-tech / out-of-domain query;
- politically framed query;
- follow-up pressure query.

Назначение routing:
- выбрать слой;
- выбрать язык;
- включить или не включить deprecated dataset;
- выбрать exact / hybrid / broad / structural mode;
- предотвратить false completeness;
- предотвратить article mismatch;
- ограничить unsafe mixing.

Если в запросе нет явных historical / comparison markers:
- `1995 deprecated` не должен участвовать как равноправный слой;
- должен применяться hard preference на `2026 norm`.

Если есть маркеры вида:
- `1995`;
- `старая редакция`;
- `сравни`;
- `было / стало`;
- `чем отличается`;
- `исторически`;
- `раньше`;

маршрутизация может разрешить подключение `1995 deprecated`.

---

## 11. EXACT LOOKUP

Если запрос содержит:
- номер статьи;
- номер пункта;
- номер подпункта;
- точную ссылку на структурный элемент;
- почти цитатный reference pattern,

retrieval должен сначала запускать exact / lexical path, а не обычный semantic retrieval.

Приоритет exact lookup:
1. lexical / structured match по article / point metadata;
2. heading / reference match;
3. body exact phrase match;
4. только затем semantic fallback.

Exact mode должен:
- повышать вес article / point совпадения;
- снижать риск соседней статьи;
- проверять, совпадает ли найденный structural unit с запросом;
- маркировать уровень точности: article-level, point-level, inferred-from-context.

Нельзя:
- отвечать по статье 42 в целом, будто найден именно пункт 2 статьи 42;
- подменять точный запрос соседней нормой без явной оговорки;
- выдавать semantic-near hit за exact match.

Если точный structural unit не найден, retrieval обязан передать answer-layer это ограничение явно.

---

## 12. STRUCTURAL CONTEXT EXPANSION

Для юридически неполных, обрезанных или отсылочных чанков retrieval должен уметь подтягивать ближайший структурный контекст.

Это особенно важно для запросов:
- по пункту / подпункту;
- с формулами вида «лица, указанные в пункте 1 настоящей статьи»;
- с отсылкой на parent article;
- с зависимостью от предыдущего или следующего структурного элемента.

Если isolated chunk нельзя правильно понять без ближайшего контекста, retrieval должен:
- подтянуть parent article;
- подтянуть соседний point / subpoint;
- сохранить различие между основным чанком и расширяющим контекстом;
- не склеивать их бесследно.

Нельзя:
- передавать answer-layer юридически неполный фрагмент как будто он самодостаточен;
- восполнять пропуск догадкой;
- терять указание, какой именно кусок был исходным match, а какой — context expansion.

---

## 13. HYBRID SEARCH

Для конституционных материалов должен использоваться hybrid retrieval, сочетающий:
- lexical / keyword matching;
- semantic / vector matching;
- metadata-aware reranking.

Роль lexical search:
- номера статей;
- номера пунктов;
- точные термины;
- устойчивые правовые формулы;
- почти цитатные запросы;
- названия институтов.

Роль semantic search:
- переформулированные вопросы;
- бытовые пользовательские формулировки;
- broad topical requests;
- comparison queries;
- simple explanation queries.

При конфликте lexical и semantic кандидатов решение должно приниматься не только по score, но и с учётом:
- layer;
- article / point match;
- language;
- status;
- deprecated marker;
- query type;
- completeness adequacy.

Semantic search не должен заменять точный поиск по юридически значимым токенам.

---

## 14. TOPICAL NORMALIZATION

Перед retrieval допустима controlled normalization пользовательских формулировок, если она:
- не меняет смысл запроса;
- не вносит новую норму;
- не сдвигает слой;
- не добавляет исторический режим без запроса;
- не превращает уточняющий вопрос в обзорный.

Разрешённые примеры нормализации:
- морфологические варианты;
- устойчивые формулы;
- эквивалентные синтаксические формы;
- topical shortcuts, уже подтверждённые retrieval QA.

Нельзя:
- нормализовывать запрос в сторону политической интерпретации;
- дописывать смысл, которого нет;
- автоматически расширять обычный запрос в historical / comparison mode;
- заменять article query общим topical query.

Если используется topical shortcut, он не должен ломать source-priority и exact behavior.

---

## 15. ШИРОКИЕ И ОБЗОРНЫЕ ЗАПРОСЫ

Если вопрос широкий, обзорный или потенциально требует полного охвата корпуса, retrieval не должен оставаться в узком top-k по умолчанию.

Для broad-query mode retrieval должен:
- расширять охват;
- искать по нескольким тематически релевантным веткам;
- собирать несколько подтверждённых `norm`-фрагментов;
- при необходимости добавлять structural grouping;
- избегать узкого случайного списка.

Broad mode нужен для вопросов типа:
- «Какие политические права есть в проекте?»;
- «Перечисли права по этой теме»;
- «Назови статьи о ...»;
- «Это всё?».

При этом retrieval всё равно не должен делать вывод о полноте.

Retrieval считается безопасным для broad query, если:
- найдено несколько релевантных norm-фрагментов;
- сохранена рамка «подтверждённые положения по найденным материалам»;
- answer-layer не провоцируется на исчерпывающий список без отдельной полной проверки.

False completeness на broad query — blocker-класс риска.

---

## 16. EXISTENCE QUERIES

Запросы вида:
- «есть ли норма о ...?»;
- «предусмотрено ли ...?»;
- «сказано ли что-то о ...?»;
- «закреплено ли ...?»,

должны обрабатываться осторожнее обычных topical queries.

Для existence query retrieval обязан различать:
- прямое подтверждение;
- косвенно похожий, но недостаточный фрагмент;
- отсутствие подтверждения в найденных материалах;
- конфликтные данные.

Нельзя:
- превращать слабое тематическое совпадение в подтверждение существования нормы;
- превращать отсутствие найденного подтверждения в категорическое «точно нет»;
- использовать commentary / faq как доказательство существования нормы без найденного `norm`.

---

## 17. SIMPLE EXPLANATION QUERY

Если пользователь просит объяснить норму простыми словами, retrieval сначала ищет `norm`, а затем только при необходимости добавляет:
- `commentary`;
- `faq`.

`Commentary` полезен для:
- пояснения сложного нормативного текста;
- объяснения процедуры;
- сопровождения comparison mode;
- пояснения уже найденной нормы.

`FAQ` полезен для:
- краткого пользовательского пояснения;
- бытовой формулировки;
- очень короткой ориентирующей справки.

Нельзя:
- использовать `commentary` вместо отсутствующего `norm`;
- использовать `faq` вместо отсутствующего `norm`;
- восстанавливать содержание нормы по commentary / faq, если `norm` не найден.

---

## 18. MIXED-TOPIC QUERIES

Если пользовательский вопрос содержит несколько разных тем, retrieval не должен насильно искать один «универсальный» фрагмент.

В mixed-topic mode retrieval должен:
- разложить запрос на подтверждаемые части;
- найти отдельные кандидаты по каждой теме;
- не склеивать несопоставимые нормы;
- не компенсировать отсутствие одного блока за счёт другого;
- передать answer-layer структуру, где видно, какие части вопроса подтверждены, а какие нет.

Нельзя:
- отвечать по части А так, будто это закрывает часть Б;
- склеивать несколько соседних тем в один псевдоответ;
- скрывать, что часть mixed-query осталась неподтверждённой.

---

## 19. POLITICAL FRAMING QUERIES

Если запрос сформулирован в политически нагруженной, оценочной или давящей рамке, retrieval не должен подстраиваться под этот framing.

Retrieval должен:
- выделять текстовую тему вопроса;
- искать нормативное содержание, а не политический нарратив;
- отдавать предпочтение text-centered norm-фрагментам;
- не поднимать commentary с политическим оттенком выше найденного norm;
- не расширять запрос в сторону мотивов, причин, выгодоприобретателей или скрытых целей.

Если в commentary-layer есть материалы с выраженным messaging-компонентом, они не должны вытеснять norm.

Правило распространяется также на фрагменты, полученные из `ce_lines_ru`. Если `ce_lines_ru` включён в контур retrieval, его содержимое (референдумные линии, контраргументы, агитационные тезисы) не должно воспроизводиться в ответах как нейтральный нормативный или разъяснительный материал. Фрагменты из `ce_lines_ru` должны передаваться с явной маркировкой `context_role=campaign-content` и НЕ допускаются в ordinary user retrieval без отдельного решения. До принятия такого решения `ce_lines_ru` считается restricted dataset.

---

## 20. WEAK / EMPTY RETRIEVAL

Если retrieval не нашёл релевантных фрагментов:
- не строить synthetic answer by guess;
- не компенсировать пробел world knowledge;
- не передавать answer-layer случайный тематически близкий шум;
- использовать safe failure.

Если retrieval нашёл только слабые, косвенные или неуверенные кандидаты:
- не маркировать их как достаточный norm support;
- повысить caution level;
- при необходимости передать answer-layer, что подтверждение неполное;
- не позволять commentary или faq замещать отсутствующий norm.

Стандарт safe-retrieval cases:
- no relevant materials found;
- only commentary found for norm-demanding query;
- only faq found for norm-demanding query;
- only weak semantic near-hit found;
- exact lookup not confirmed;
- structural unit incomplete.

---

## 21. ДОСТАТОЧНОСТЬ RETRIEVAL

Retrieval считается достаточным для ответа, если найден хотя бы один `2026 norm`-фрагмент, который:
- прямо относится к теме вопроса;
- подтверждает ключевой тезис ответа;
- не требует домысливания критического элемента;
- не заменяется commentary;
- не является случайным близким куском.

Для exact lookup достаточность означает:
- найден нужный article / point;
- или явно найден article-level fragment и отдельно указано, что point-level не подтверждён.

Для comparison query достаточность означает:
- найден как минимум один релевантный `2026 norm`;
- найден как минимум один сопоставимый `1995 deprecated`, если comparison действительно запрошен;
- различие между ними можно описать без догадок.

Для broad query достаточность означает:
- retrieval дал несколько подтверждённых фрагментов;
- видно, что это не случайный единичный top-k;
- сохранена рамка не-исчерпывающего перечисления.

Retrieval недостаточен, если:
- найден только `commentary` без `norm`, а вопрос требует нормативного ответа;
- найден только isolated chunk без нужного structural context;
- найден только semantic near-hit;
- exact query не подтверждён;
- результаты конфликтуют, а metadata не передана;
- выдача допускает несколько трактовок, но retrieval не развёл их.

---

## 22. COMMENTARY И FAQ: ПРАВИЛА ДОБАВЛЕНИЯ

`Commentary` и `faq` — это не источник установления нормы, а supporting context.

Они допустимы, только если выполняются оба условия:
1. сначала найден релевантный `norm`;
2. вопрос действительно требует пояснения, упрощения или сопровождающего контекста.

Если commentary / faq добавляются, retrieval обязан:
- передавать их отдельно от `norm`;
- сохранять layer metadata;
- не смешивать их в один неразличимый текстовый блок;
- не позволять answer-layer принять их за основной нормативный источник.

Нельзя:
- использовать commentary / faq как substitute for missing norm;
- использовать faq как доказательство существования права;
- использовать commentary для восстановления номера статьи;
- повышать commentary-layer до уровня norm только потому, что он более «понятный».

---

## 23. ДОПОЛНИТЕЛЬНЫЕ ДОКУМЕНТЫ И ГРАНИЦА КОНТУРА

Дополнительные operational, campaign, internal или штабные документы не считаются production-ready knowledge base автоматически.

До отдельного решения такие материалы не должны автоматически попадать в ordinary user retrieval.

Для новых документов обязательный порядок:
1. inventory;
2. classification;
3. canonical file selection;
4. extraction / normalization;
5. deduplication;
6. решение: commentary-layer или internal-only;
7. import;
8. SQL QA;
9. retrieval QA;
10. только после этого допуск в chatbot-контур.

Критические правила:
- новые документы не должны загрязнять `norm`-слой;
- internal / restricted материалы не должны попасть в ordinary user retrieval;
- commentary-ready документы не должны автоматически трактоваться как norm;
- решение по новым документам не должно ломать текущий release gate answer-layer QA.

---

## 24. ИЗОЛЯЦИЯ СЛОЁВ И СБОРКА КОНТЕКСТА

Retrieval не должен смешивать слои в один неразличимый массив текста.

Каждый retrieved fragment должен сохранять явную маркировку:
- `dataset`;
- `layer`;
- `language`;
- `status`;
- `article`;
- `point`;
- `deprecated`;
- `effective_date`, если есть;
- `body`.

Если retrieved fragments относятся к одной теме, их можно собирать в bundle, но только с сохранением ролей:
- `norm` — основа;
- `commentary` — пояснение;
- `faq` — упрощение;
- `1995 deprecated` — отдельный historical/comparison layer.

Нельзя склеивать:
- `2026 norm` и `1995 deprecated` в одно утверждение без comparison mode;
- `commentary` и `norm` как будто это один текст;
- `faq` и `norm` как будто faq доказывает норму;
- несопоставимые куски только потому, что они похожи по semantic score.

---

## 25. CONFLICTING FRAGMENTS

Если retrieval находит фрагменты, которые расходятся:
- по формулировке;
- по статусу;
- по временному режиму;
- по степени конкретности;
- по слою;
- по редакции;
- по article / point;
- по языковой версии,

retrieval не должен скрывать это расхождение.

Вместо этого он должен:
- передать конфликтующие кандидаты вместе;
- сохранить различающие metadata;
- не выбирать один фрагмент только по score, если metadata указывает на возможный статусный или редакционный конфликт;
- явно пометить набор как conflict-sensitive.

Если без дополнительного контекста расхождение не снимается, retrieval должен передать answer-layer именно это ограничение, а не псевдо-однозначный ответ.

---

## 26. RANKING ПРАВИЛА

При reranking кандидатов нужно учитывать как минимум:

1. layer priority;
2. exact structural match;
3. language match;
4. status compatibility;
5. deprecated penalty / hard exclusion в ordinary mode;
6. norm support adequacy;
7. topical relevance;
8. completeness fitness for query type;
9. context sufficiency;
10. conflict sensitivity.

Условные приоритеты:
- exact article / point match выше general topical similarity;
- `2026 norm` выше `commentary`, даже если commentary текстово «удобнее»;
- `2026 norm` выше `1995 deprecated` в ordinary mode;
- bundle с parent context выше isolated incomplete chunk;
- несколько согласованных norm-фрагментов выше одного случайного broad hit для обзорного вопроса.

---

## 27. МИНИМАЛЬНЫЙ ВЫХОД RETRIEVAL В ANSWER-LAYER

В answer-layer должны передаваться не только тексты, но и необходимые ограничители интерпретации.

Минимально полезный fragment payload:
- `dataset`
- `layer`
- `language`
- `status`
- `deprecated`
- `article`
- `point`
- `body`

Желательно также:
- `heading`
- `effective_date`
- `entry_into_force`
- `chunk_index`
- `context_role` (`primary_match`, `supporting_context`, `comparison_match`, `structural_parent`, `fallback_only`)
- `confidence_mode` (`exact`, `broad`, `semantic-near`, `structural-expanded`, `weak`)

Без этих полей answer-layer легче:
- подменить layer;
- стереть статус;
- выдать comparison за ordinary answer;
- перепутать article / point;
- потерять границу между norm и explanation.

---

## 28. ПЛОХИЕ И ХОРОШИЕ ПАТТЕРНЫ RETRIEVAL

Хороший retrieval:
- возвращает приоритетно правильный слой;
- не допускает deprecated leakage;
- не подменяет norm commentary;
- не теряет article / point;
- расширяет context при отсылочной норме;
- расширяет coverage на broad query;
- сохраняет project / transition / deprecated markers;
- не провоцирует answer-layer на false completeness;
- не маскирует weak retrieval под уверенный.

Плохой retrieval:
- выдаёт `1995 deprecated` как default current norm;
- подменяет `norm` commentary;
- теряет статус и происхождение фрагмента;
- отвечает по соседней статье как по точной;
- режет юридически значимый parent context;
- даёт узкий случайный top-k на обзорный вопрос;
- склеивает разные слои и темы;
- передаёт weak semantic hit как достаточное подтверждение нормы.

---

## 29. QA-СВЯЗКА С RED-TEAM

Эта retrieval-policy должна проверяться не только на offline relevance, но и через red-team / functional QA сценарии.

Критические retrieval-sensitive кейсы:
- `1995 deprecated` leakage;
- false completeness на broad queries;
- commentary / faq substitution;
- exact article mismatch;
- point mismatch;
- weak retrieval hallucination pressure;
- mixed-topic unsafe merge;
- status mislabeling;
- unsafe comparison merge.

Если retrieval проваливает хотя бы один blocker-класс кейсов, release status answer-layer остаётся `NO-GO` до фикса и retest.

---

## 30. RELEASE-КРИТЕРИЙ ДЛЯ RETRIEVAL-СЛОЯ

Retrieval-layer можно считать operationally acceptable только если одновременно выполнено следующее:
- ordinary current-layer queries приоритетно разрешаются через `2026 norm`;
- `1995 deprecated` не всплывает как default current norm;
- exact lookup не подменяет article / point соседним фрагментом;
- broad retrieval не провоцирует false completeness;
- weak retrieval не передаётся как уверенный norm support;
- commentary / faq не заменяют norm;
- status markers не теряются;
- comparison mode держит раздельность слоёв;
- mixed-topic queries не склеиваются небезопасно;
- есть QA-подтверждение через critical red-team cases.

До подтверждения этого через QA-run retrieval-layer нельзя считать production-ready сам по себе.

---

## 31. ИТОГОВАЯ ДИСЦИПЛИНА

В каждом запросе retrieval обязан соблюдать следующий порядок:

1. определить тип запроса;
2. выбрать правильный слой;
3. выбрать правильный язык;
4. защитить `2026 norm` от подмены `1995 deprecated`;
5. применить exact path там, где нужен exact path;
6. применить hybrid retrieval там, где нужен topical поиск;
7. подтянуть structural context там, где isolated chunk опасен;
8. расширить coverage для broad query;
9. сохранить metadata и layer separation;
10. передать answer-layer только интерпретируемый и безопасный контекст.

Если есть выбор между:
- «более удобной, но рискованной выдачей»
и
- «более осторожной, но корректно ограниченной выдачей»,

retrieval должен выбирать осторожную и корректно ограниченную выдачу.
