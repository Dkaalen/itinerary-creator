// Local Library normalization and versioned ranking-contract ownership.

(() => {
  'use strict';

  let preparedNormalizationVersion = '';
  let preparedNormalizationRuntime = null;
  let preparedRankingRuntimeVersion = '';
  let preparedRankingRuntime = null;

  function normalizationRuntime(rankingSpec = {}) {
    const version = String(rankingSpec.version || '');
    if (version && version === preparedNormalizationVersion && preparedNormalizationRuntime) {
      return preparedNormalizationRuntime;
    }
    const normalization = rankingSpec.normalization || {};
    const runtime = {
      unicodeForm: String(normalization.unicode_form || 'NFKD'),
      transliteration: Object.entries(normalization.transliteration || {}).map(([source, replacement]) => (
        [String(source), String(replacement)]
      )),
    };
    if (version) {
      preparedNormalizationVersion = version;
      preparedNormalizationRuntime = runtime;
    }
    return runtime;
  }

  function normalizeSearchText(value, rankingSpec = {}) {
    const runtime = normalizationRuntime(rankingSpec);
    let text = String(value || '').toLowerCase();
    for (const [source, replacement] of runtime.transliteration) {
      text = text.split(source).join(replacement);
    }
    return text
      .normalize(runtime.unicodeForm)
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim()
      .replace(/\s+/g, ' ');
  }

  function normalizedAliasValues(values, rankingSpec = {}) {
    return (values || []).map((value) => normalizeSearchText(value, rankingSpec)).filter(Boolean);
  }

  function libraryRankingRuntime(rankingSpec = {}) {
    const version = String(rankingSpec.version || '');
    if (version && version === preparedRankingRuntimeVersion && preparedRankingRuntime) {
      return preparedRankingRuntime;
    }
    const runtime = {
      version,
      minimumQueryLength: Number(rankingSpec.minimum_query_length || 2),
      fieldRules: Array.isArray(rankingSpec.search_fields)
        ? rankingSpec.search_fields.filter((rule) => rule && rule.name).map((rule) => ({
            name: String(rule.name),
            weight: Number(rule.weight || 0),
          }))
        : [],
      matchWeights: Object.fromEntries(
        Object.entries(rankingSpec.match_weights || {}).map(([key, value]) => [key, Number(value || 0)])
      ),
      contextWeights: Object.fromEntries(
        Object.entries(rankingSpec.context_weights || {}).map(([key, value]) => [key, Number(value || 0)])
      ),
      routes: (rankingSpec.sheet_routes || []).map((route) => ({
        sheet: normalizeSearchText(route.sheet, rankingSpec),
        terms: (route.terms || []).map((term) => normalizeSearchText(term, rankingSpec)).filter(Boolean),
      })),
      aliases: (rankingSpec.cross_type_aliases || []).map((alias) => ({
        id: String(alias.id || ''),
        phrase: normalizeSearchText(alias.phrase, rankingSpec),
        contextTypes: normalizedAliasValues(alias.context_types, rankingSpec),
        contextSheets: normalizedAliasValues(alias.context_sheets, rankingSpec),
        sourceTypes: normalizedAliasValues(alias.source_types, rankingSpec),
        sourceSheets: normalizedAliasValues(alias.source_sheets, rankingSpec),
      })),
      tieBreak: Array.isArray(rankingSpec.tie_break) ? rankingSpec.tie_break.map(String) : [],
    };
    if (version) {
      preparedRankingRuntimeVersion = version;
      preparedRankingRuntime = runtime;
    }
    return runtime;
  }

  window.ItineraryCalculator.define('library.normalization', {
    libraryRankingRuntime,
    normalizeSearchText,
  });
})();
