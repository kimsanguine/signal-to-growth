-- Operational category (category_tag) and discovery theme are two different
-- taxonomies per P6-C02-Clip01: the same inquiry gets an operational tag
-- ("환불", "버그", "사용법" — who handles it, how urgent) and a separate
-- discovery tag (what recurring friction this points to — e.g. "온보딩
-- 단계에서 가치를 못 느낌"). Conflating them into one field means discovery
-- signal gets buried under whatever operational tag was fastest to apply.
-- category_tag was already free-text (no CHECK constraint), so the label
-- set can grow without a schema change; this migration only adds the
-- separate discovery_theme column.

alter table public.kakao_cs_events_habix_legal
  add column if not exists discovery_theme text;

alter table public.kakao_cs_events_habix_course
  add column if not exists discovery_theme text;
