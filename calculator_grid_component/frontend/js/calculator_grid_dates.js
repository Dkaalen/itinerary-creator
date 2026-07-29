const DATE_MODE_LINKED = 'linked';
const DATE_MODE_LOCKED = 'locked';

function parseDayNumber(value) {
  const text = String(value || '').trim().toLowerCase();
  if (!text) return null;
  const match = text.match(/^(?:d|day)?\s*(\d+)$/);
  if (!match) return null;
  const day = Number.parseInt(match[1], 10);
  return Number.isFinite(day) && day > 0 ? day : null;
}

function parseGridDate(value) {
  const text = String(value || '').trim();
  let match = text.match(/^(\d{1,2})[.\/-](\d{1,2})[.\/-](\d{4})$/);
  if (match) {
    return buildDateParseResult(Number(match[3]), Number(match[2]), Number(match[1]), text.includes('/') ? 'slash' : text.includes('-') ? 'dash' : 'dot');
  }
  match = text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (match) {
    return buildDateParseResult(Number(match[1]), Number(match[2]), Number(match[3]), 'iso');
  }
  return null;
}

function buildDateParseResult(year, month, day, format) {
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
  return {date, format};
}

function addDays(date, days) {
  const next = new Date(date.getTime());
  next.setUTCDate(next.getUTCDate() + days);
  return next;
}

function dateDifferenceDays(later, earlier) {
  return Math.round((later.getTime() - earlier.getTime()) / 86400000);
}

function formatGridDate(date, format) {
  const day = String(date.getUTCDate()).padStart(2, '0');
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const year = String(date.getUTCFullYear());
  if (format === 'iso') return `${year}-${month}-${day}`;
  if (format === 'slash') return `${day}/${month}/${year}`;
  if (format === 'dash') return `${day}-${month}-${year}`;
  return `${day}.${month}.${year}`;
}

function normalizeDateMode(value) {
  const text = String(value || '').trim().toLowerCase();
  return text === DATE_MODE_LINKED || text === DATE_MODE_LOCKED ? text : '';
}

function optionalInteger(value) {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) ? parsed : null;
}

function inferTripStartDate(rows) {
  let earliest = null;
  for (const row of rows || []) {
    const parsed = parseGridDate(row.from_date);
    if (!parsed) continue;
    if (parseDayNumber(row.day) === 1) return formatGridDate(parsed.date, 'iso');
    if (!earliest || parsed.date < earliest) earliest = parsed.date;
  }
  return earliest ? formatGridDate(earliest, 'iso') : '';
}

function arrivalDateContext(rows, explicitStartDate = '') {
  const explicit = parseGridDate(explicitStartDate);
  if (explicit) return {date: explicit.date, format: explicit.format};
  const inferred = parseGridDate(inferTripStartDate(rows));
  return inferred ? {date: inferred.date, format: inferred.format} : null;
}

function initializeDateRelationships(rows, explicitStartDate = '') {
  const startText = String(explicitStartDate || '').trim() || inferTripStartDate(rows);
  const context = arrivalDateContext(rows, startText);
  if (!context) return startText;
  const startDate = context.date;
  for (const row of rows || []) {
    const dayNumber = parseDayNumber(row.day);
    const fromParsed = parseGridDate(row.from_date);
    const toParsed = parseGridDate(row.to_date);

    let fromMode = normalizeDateMode(row.from_date_mode);
    let fromOffset = optionalInteger(row.from_date_offset);
    if (!fromMode) {
      if (!String(row.from_date || '').trim() && dayNumber) {
        fromMode = DATE_MODE_LINKED;
        fromOffset = dayNumber - 1;
      } else if (fromParsed && dayNumber && dateDifferenceDays(fromParsed.date, startDate) === dayNumber - 1) {
        fromMode = DATE_MODE_LINKED;
        fromOffset = dayNumber - 1;
      } else if (fromParsed) {
        fromMode = DATE_MODE_LOCKED;
        fromOffset = null;
      } else {
        fromMode = '';
        fromOffset = null;
      }
    } else if (fromMode === DATE_MODE_LINKED && fromOffset === null) {
      if (dayNumber) fromOffset = dayNumber - 1;
      else if (fromParsed) fromOffset = dateDifferenceDays(fromParsed.date, startDate);
    }

    let toMode = normalizeDateMode(row.to_date_mode);
    let toOffset = optionalInteger(row.to_date_offset);
    if (!toMode) {
      if (toParsed) {
        toMode = DATE_MODE_LINKED;
        toOffset = dateDifferenceDays(toParsed.date, startDate);
      } else {
        toMode = '';
        toOffset = null;
      }
    } else if (toMode === DATE_MODE_LINKED && toOffset === null && toParsed) {
      toOffset = dateDifferenceDays(toParsed.date, startDate);
    }

    row.from_date_mode = fromMode;
    row.from_date_offset = fromOffset;
    row.to_date_mode = toMode;
    row.to_date_offset = toOffset;
  }
  return formatGridDate(startDate, 'iso');
}

function shiftLinkedDates(rows, oldStartValue, newStartValue) {
  const oldStart = parseGridDate(oldStartValue);
  const newStart = parseGridDate(newStartValue);
  if (!newStart) return false;
  let changed = false;
  for (const row of rows || []) {
    for (const key of ['from_date', 'to_date']) {
      if ((normalizeDateMode(row[`${key}_mode`]) || DATE_MODE_LINKED) !== DATE_MODE_LINKED) continue;
      let offset = optionalInteger(row[`${key}_offset`]);
      const parsed = parseGridDate(row[key]);
      if (offset === null && key === 'from_date') {
        const dayNumber = parseDayNumber(row.day);
        if (dayNumber) offset = dayNumber - 1;
      }
      if (offset === null && parsed && oldStart) offset = dateDifferenceDays(parsed.date, oldStart.date);
      if (offset === null) continue;
      const format = parsed?.format || (key === 'from_date' ? 'dot' : newStart.format);
      const next = formatGridDate(addDays(newStart.date, offset), format);
      if (row[key] !== next || row[`${key}_offset`] !== offset) {
        row[key] = next;
        row[`${key}_offset`] = offset;
        changed = true;
      }
    }
  }
  return changed;
}

function setTripStartDate(state, rawValue) {
  const parsed = parseGridDate(rawValue);
  if (!state || !parsed) return false;
  const nextStart = formatGridDate(parsed.date, 'iso');
  const oldStart = String(state.tripStartDate || '').trim() || inferTripStartDate(state.rows);
  initializeDateRelationships(state.rows, oldStart || nextStart);
  const changed = shiftLinkedDates(state.rows, oldStart || nextStart, nextStart);
  if (state.tripStartDate !== nextStart) {
    state.tripStartDate = nextStart;
    return true;
  }
  return changed;
}

function applyDeferredTripStartDate(state) {
  if (!state) return false;
  const pending = String(state._pendingTripStartDate || '').trim();
  delete state._pendingTripStartDate;
  return pending ? setTripStartDate(state, pending) : false;
}

function markDateManualState(row, key, rawValue) {
  if (key !== 'from_date' && key !== 'to_date') return;
  const text = String(rawValue || '').trim();
  if (!text) {
    const dayNumber = key === 'from_date' ? parseDayNumber(row.day) : null;
    row[`${key}_mode`] = dayNumber ? DATE_MODE_LINKED : '';
    row[`${key}_offset`] = dayNumber ? dayNumber - 1 : null;
    return;
  }
  row[`${key}_mode`] = DATE_MODE_LOCKED;
  row[`${key}_offset`] = null;
}

function markDayChanged(row) {
  if (normalizeDateMode(row.from_date_mode) === DATE_MODE_LOCKED) return;
  row.from_date_mode = DATE_MODE_LINKED;
  const dayNumber = parseDayNumber(row.day);
  row.from_date_offset = dayNumber ? dayNumber - 1 : null;
}

function autofillDatesFromArrival(rows, explicitStartDate = '') {
  const stateStart = String(explicitStartDate || (typeof calculatorState !== 'undefined' && calculatorState ? calculatorState.tripStartDate : '') || '').trim();
  const context = arrivalDateContext(rows, stateStart);
  if (!context) return false;
  const normalizedStart = formatGridDate(context.date, 'iso');
  if (typeof calculatorState !== 'undefined' && calculatorState && !calculatorState.tripStartDate) {
    calculatorState.tripStartDate = normalizedStart;
  }
  initializeDateRelationships(rows, normalizedStart);
  let changed = false;
  for (const row of rows || []) {
    const dayNumber = parseDayNumber(row.day);
    if (!dayNumber) continue;
    if (normalizeDateMode(row.from_date_mode) === DATE_MODE_LOCKED) continue;
    const offset = optionalInteger(row.from_date_offset) ?? dayNumber - 1;
    const current = parseGridDate(row.from_date);
    const next = formatGridDate(addDays(context.date, offset), current?.format || 'dot');
    if (row.from_date !== next || row.from_date_offset !== offset || row.from_date_mode !== DATE_MODE_LINKED) {
      row.from_date = next;
      row.from_date_offset = offset;
      row.from_date_mode = DATE_MODE_LINKED;
      changed = true;
    }
  }
  return changed;
}

function selectedDateCells() {
  const selection = normalizedSelection();
  if (!selection) return [];
  const columns = visibleColumns(calculatorState.showAdvanced);
  const result = [];
  for (let rowIndex = selection.top; rowIndex <= selection.bottom; rowIndex += 1) {
    for (let colIndex = selection.left; colIndex <= selection.right; colIndex += 1) {
      const key = columns[colIndex]?.key;
      if (key === 'from_date' || key === 'to_date') result.push({rowIndex, key});
    }
  }
  return result;
}

function setSelectedDateMode(mode) {
  const cells = selectedDateCells();
  if (!cells.length) return false;
  const start = parseGridDate(calculatorState.tripStartDate || inferTripStartDate(calculatorState.rows));
  if (!start) return false;
  recordHistory();
  for (const {rowIndex, key} of cells) {
    const row = calculatorState.rows[rowIndex];
    if (!row) continue;
    row[`${key}_mode`] = mode;
    if (mode === DATE_MODE_LOCKED) {
      row[`${key}_offset`] = null;
      continue;
    }
    const parsed = parseGridDate(row[key]);
    if (key === 'from_date') {
      const dayNumber = parseDayNumber(row.day);
      row.from_date_offset = dayNumber ? dayNumber - 1 : (parsed ? dateDifferenceDays(parsed.date, start.date) : null);
    } else {
      row.to_date_offset = parsed ? dateDifferenceDays(parsed.date, start.date) : null;
    }
  }
  autofillDatesFromArrival(calculatorState.rows, calculatorState.tripStartDate);
  markLocalDraft();
  rerender();
  return true;
}

function dateCellMode(row, key) {
  if (key !== 'from_date' && key !== 'to_date') return '';
  if (!String(row?.[key] || '').trim() && !(key === 'from_date' && parseDayNumber(row?.day))) return '';
  return normalizeDateMode(row?.[`${key}_mode`]) || DATE_MODE_LINKED;
}
