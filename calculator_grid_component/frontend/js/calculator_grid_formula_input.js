// Safe spreadsheet-style numeric input parser. Supports arithmetic, percentages, and A1 references.
function parseNumericInput(value, referenceResolver = null) {
  try {
    return evaluateNumericInput(value, referenceResolver);
  } catch (_error) {
    return null;
  }
}

function evaluateNumericInput(value, referenceResolver = null) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('#VALUE!');
    return value;
  }
  const text = normalizeNumericExpression(value);
  if (!text || ['none', 'nan', 'null'].includes(text.toLowerCase())) return null;
  const parser = new NumericExpressionParser(text, referenceResolver);
  const result = parser.parseExpression();
  parser.skipWhitespace();
  if (!parser.isAtEnd()) throw new Error('#VALUE!');
  if (!Number.isFinite(result)) throw new Error('#VALUE!');
  return result;
}

function normalizeNumericExpression(value) {
  let text = String(value || '').trim().replaceAll(',', '.');
  if (text.startsWith('=')) text = text.slice(1).trim();
  return text;
}

class NumericExpressionParser {
  constructor(text, referenceResolver = null) {
    this.text = text;
    this.index = 0;
    this.referenceResolver = referenceResolver;
  }

  isAtEnd() {
    return this.index >= this.text.length;
  }

  skipWhitespace() {
    while (!this.isAtEnd() && /\s/.test(this.text[this.index])) this.index += 1;
  }

  parseExpression() {
    let value = this.parseTerm();
    while (true) {
      this.skipWhitespace();
      const operator = this.text[this.index];
      if (operator !== '+' && operator !== '-') return value;
      this.index += 1;
      const right = this.parseTerm();
      value = operator === '+' ? value + right : value - right;
    }
  }

  parseTerm() {
    let value = this.parseFactor();
    while (true) {
      this.skipWhitespace();
      const operator = this.text[this.index];
      if (operator !== '*' && operator !== '/') return value;
      this.index += 1;
      const right = this.parseFactor();
      if (operator === '/' && right === 0) throw new Error('#DIV/0!');
      value = operator === '*' ? value * right : value / right;
    }
  }

  parseFactor() {
    this.skipWhitespace();
    const char = this.text[this.index];
    if (char === '+') {
      this.index += 1;
      return this.parseFactor();
    }
    if (char === '-') {
      this.index += 1;
      return -this.parseFactor();
    }
    let value;
    if (char === '(') {
      this.index += 1;
      value = this.parseExpression();
      this.skipWhitespace();
      if (this.text[this.index] !== ')') throw new Error('#VALUE!');
      this.index += 1;
    } else if (char === '$' || /[A-Za-z]/.test(char || '')) {
      value = this.parseReference();
    } else {
      value = this.parseNumber();
    }
    this.skipWhitespace();
    if (this.text[this.index] === '%') {
      this.index += 1;
      value /= 100;
    }
    return value;
  }

  parseReference() {
    const match = this.text.slice(this.index).match(/^\$?([A-Za-z]{1,2})\$?(\d+)/);
    if (!match) throw new Error('#REF!');
    if (typeof this.referenceResolver !== 'function') throw new Error('#REF!');
    this.index += match[0].length;
    const reference = `${match[1].toUpperCase()}${Number(match[2])}`;
    const value = this.referenceResolver(reference);
    if (!Number.isFinite(value)) throw new Error('#VALUE!');
    return value;
  }

  parseNumber() {
    this.skipWhitespace();
    const match = this.text.slice(this.index).match(/^(?:\d+(?:\.\d*)?|\.\d+)/);
    if (!match) throw new Error('#VALUE!');
    this.index += match[0].length;
    return Number(match[0]);
  }
}

function translateFormulaReferences(value, rowDelta, columnDelta) {
  const text = String(value ?? '');
  if (!text.trim().startsWith('=')) return value;
  return text.replace(/(\$?)([A-Za-z]{1,2})(\$?)(\d+)/g, (_match, absoluteColumn, letters, absoluteRow, rowText) => {
    let columnNumber = spreadsheetColumnNumber(letters.toUpperCase());
    let rowNumber = Number(rowText);
    if (!absoluteColumn) columnNumber += Number(columnDelta || 0);
    if (!absoluteRow) rowNumber += Number(rowDelta || 0);
    if (columnNumber < 1 || rowNumber < 1) return '#REF!';
    return `${absoluteColumn}${spreadsheetColumnLetters(columnNumber)}${absoluteRow}${rowNumber}`;
  });
}

function spreadsheetColumnNumber(letters) {
  let value = 0;
  for (const char of String(letters || '').toUpperCase()) value = value * 26 + char.charCodeAt(0) - 64;
  return value;
}

function spreadsheetColumnLetters(number) {
  let value = Number(number);
  let letters = '';
  while (value > 0) {
    value -= 1;
    letters = String.fromCharCode(65 + (value % 26)) + letters;
    value = Math.floor(value / 26);
  }
  return letters;
}
