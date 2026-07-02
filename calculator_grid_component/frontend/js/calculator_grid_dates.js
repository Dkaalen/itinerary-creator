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
  let match = text.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$/);
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

function formatGridDate(date, format) {
  const day = String(date.getUTCDate()).padStart(2, '0');
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const year = String(date.getUTCFullYear());
  if (format === 'iso') return `${year}-${month}-${day}`;
  if (format === 'slash') return `${day}/${month}/${year}`;
  if (format === 'dash') return `${day}-${month}-${year}`;
  return `${day}.${month}.${year}`;
}

function arrivalDateContext(rows) {
  for (const row of rows || []) {
    if (parseDayNumber(row.day) !== 1) continue;
    const parsed = parseGridDate(row.from_date);
    if (parsed) return parsed;
  }
  return null;
}

function autofillDatesFromArrival(rows) {
  const context = arrivalDateContext(rows);
  if (!context) return false;
  let changed = false;
  for (const row of rows || []) {
    if (String(row.from_date || '').trim()) continue;
    const dayNumber = parseDayNumber(row.day);
    if (!dayNumber) continue;
    row.from_date = formatGridDate(addDays(context.date, dayNumber - 1), context.format);
    changed = true;
  }
  return changed;
}
