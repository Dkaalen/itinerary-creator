// Local Library query preparation, ranking, aliases, and deterministic ordering.

(() => {
  'use strict';

  const normalization = window.ItineraryCalculator.require('library.normalization');
  const indexApi = window.ItineraryCalculator.require('library.index');

  function expectedLibrarySheetFromRuntime(rowType, travelElement, rankingSpec, runtime) {
    const text = normalization.normalizeSearchText(`${rowType || ''} ${travelElement || ''}`, rankingSpec);
    for (const route of runtime.routes) {
      if (route.terms.some((term) => text.includes(term))) return route.sheet;
    }
    return '';
  }

  function expectedLibrarySheet(rowType, travelElement, rankingSpec = {}) {
    return expectedLibrarySheetFromRuntime(
      rowType,
      travelElement,
      rankingSpec,
      normalization.libraryRankingRuntime(rankingSpec)
    );
  }

  function prepareLibrarySearchRequest(query, context = {}, rankingSpec = {}, runtime = normalization.libraryRankingRuntime(rankingSpec)) {
    const normalizedQuery = normalization.normalizeSearchText(query, rankingSpec);
    const rowType = normalization.normalizeSearchText(context.type, rankingSpec);
    const expectedSheet = expectedLibrarySheetFromRuntime(rowType, context.travel_element, rankingSpec, runtime);
    const aliases = runtime.aliases.filter((alias) => (
      alias.phrase
      && normalizedQuery.includes(alias.phrase)
      && alias.contextTypes.includes(rowType)
      && (!expectedSheet || alias.contextSheets.includes(expectedSheet))
    ));
    return {
      normalizedQuery,
      queryTokens: normalizedQuery.split(/\s+/).filter(Boolean),
      rowType,
      expectedSheet,
      rowText: normalization.normalizeSearchText(
        [context.travel_element, context.supplier, context.comments].filter(Boolean).join(' '),
        rankingSpec
      ),
      contextSupplier: normalization.normalizeSearchText(context.supplier, rankingSpec),
      aliases,
      runtime,
    };
  }

  function libraryFieldMatchScore(text, fieldTokens, normalizedQuery, queryTokens, matchWeights = {}) {
    if (!text) return 0;
    let score = 0;
    if (text === normalizedQuery) score += matchWeights.query_exact || 0;
    else if (text.startsWith(normalizedQuery)) score += matchWeights.query_prefix || 0;
    else if (text.includes(normalizedQuery)) score += matchWeights.query_contains || 0;

    for (const token of queryTokens) {
      if (fieldTokens.includes(token)) score += matchWeights.token_exact || 0;
      else if (fieldTokens.some((fieldToken) => fieldToken.startsWith(token))) score += matchWeights.token_prefix || 0;
      else if (text.includes(token)) score += matchWeights.token_contains || 0;
    }
    return score;
  }

  function matchingPreparedCrossTypeAlias(item, request) {
    for (const alias of request.aliases) {
      if (!item._normalized_search_blob.includes(alias.phrase)) continue;
      if (!alias.sourceTypes.includes(item._normalized_type)) continue;
      if (!alias.sourceSheets.includes(item._normalized_sheet)) continue;
      return alias;
    }
    return null;
  }

  function preparedContextScore(item, request) {
    const weights = request.runtime.contextWeights;
    const alias = matchingPreparedCrossTypeAlias(item, request);
    let score = 0;
    if (request.expectedSheet && item._normalized_sheet) {
      if (item._normalized_sheet === request.expectedSheet) score += weights.sheet_exact || 0;
      else if (alias) score += weights.sheet_alias || 0;
      else score += weights.sheet_mismatch || 0;
    }
    if (request.rowType && item._normalized_type) {
      if (item._normalized_type === request.rowType) score += weights.type_exact || 0;
      else if (alias) score += weights.type_alias || 0;
      else if (item._normalized_type.includes(request.rowType) || request.rowType.includes(item._normalized_type)) {
        score += weights.type_partial || 0;
      } else score += weights.type_mismatch || 0;
    }
    if (item._normalized_country && request.rowText.includes(item._normalized_country)) {
      score += weights.country_in_context || 0;
    }
    if (item._normalized_supplier && request.contextSupplier === item._normalized_supplier) {
      score += weights.supplier_exact || 0;
    }
    if (item._normalized_supplier && request.rowText.includes(item._normalized_supplier)) {
      score += weights.supplier_in_context || 0;
    }
    return score;
  }

  function scorePreparedLibraryItem(item, request) {
    if (request.normalizedQuery.length < request.runtime.minimumQueryLength) return 0;
    let score = 0;
    item._normalized_fields.forEach((text, index) => {
      const fieldScore = libraryFieldMatchScore(
        text,
        item._normalized_field_tokens[index] || [],
        request.normalizedQuery,
        request.queryTokens,
        request.runtime.matchWeights
      );
      score += fieldScore * Number(request.runtime.fieldRules[index]?.weight || 0);
    });
    return score + preparedContextScore(item, request);
  }

  function scoreLibraryItem(item, query, context = {}, rankingSpec = {}) {
    const runtime = normalization.libraryRankingRuntime(rankingSpec);
    const request = prepareLibrarySearchRequest(query, context, rankingSpec, runtime);
    return scorePreparedLibraryItem(item, request);
  }

  function candidateLibraryIndexes(libraryRows, request, searchIndex) {
    if (!searchIndex) return libraryRows.map((_item, index) => index);
    const candidates = new Set();
    for (const bigram of indexApi.searchBigramsFromNormalized(request.normalizedQuery)) {
      for (const index of searchIndex.bigrams.get(bigram) || []) candidates.add(index);
    }
    for (const index of searchIndex.sheets.get(request.expectedSheet) || []) candidates.add(index);
    for (const index of searchIndex.types.get(request.rowType) || []) candidates.add(index);
    return candidates.size ? [...candidates] : libraryRows.map((_item, index) => index);
  }

  function compareLibraryItems(left, right, rankingSpec = {}, runtime = normalization.libraryRankingRuntime(rankingSpec)) {
    const leftValues = left._tie_break_values || runtime.tieBreak.map((fieldName) => indexApi.libraryTieBreakValue(left, fieldName, rankingSpec));
    const rightValues = right._tie_break_values || runtime.tieBreak.map((fieldName) => indexApi.libraryTieBreakValue(right, fieldName, rankingSpec));
    for (let index = 0; index < runtime.tieBreak.length; index += 1) {
      const leftValue = leftValues[index];
      const rightValue = rightValues[index];
      if (leftValue < rightValue) return -1;
      if (leftValue > rightValue) return 1;
    }
    return 0;
  }

  function findLibrarySuggestions(libraryRows, query, limit = 8, context = {}, searchIndex = null, rankingSpec = {}) {
    const runtime = normalization.libraryRankingRuntime(rankingSpec);
    const request = prepareLibrarySearchRequest(query, context, rankingSpec, runtime);
    return candidateLibraryIndexes(libraryRows || [], request, searchIndex)
      .map((index) => libraryRows[index])
      .filter(Boolean)
      .map((item) => ({item, score: scorePreparedLibraryItem(item, request)}))
      .filter((result) => result.score > 0)
      .sort((a, b) => b.score - a.score || compareLibraryItems(a.item, b.item, rankingSpec, runtime))
      .slice(0, limit);
  }

  window.ItineraryCalculator.define('library.search', {
    compareLibraryItems,
    expectedLibrarySheet,
    findLibrarySuggestions,
    scoreLibraryItem,
  });
})();
