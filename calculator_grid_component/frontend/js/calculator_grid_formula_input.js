// Safe spreadsheet-style numeric input parser. Supports =, +, -, *, /, parentheses, and percent literals.
function parseNumericInput(value) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  const text = normalizeNumericExpression(value);
  if (!text || ['none', 'nan', 'null'].includes(text.toLowerCase())) return null;
  try {
    const parser = new NumericExpressionParser(text);
    const result = parser.parseExpression();
    parser.skipWhitespace();
    if (!parser.isAtEnd()) return null;
    return Number.isFinite(result) ? result : null;
  } catch (_error) {
    return null;
  }
}

function normalizeNumericExpression(value) {
  let text = String(value || '').trim().replaceAll(',', '.');
  if (text.startsWith('=')) text = text.slice(1).trim();
  return text;
}

class NumericExpressionParser {
  constructor(text) {
    this.text = text;
    this.index = 0;
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
      if (operator === '/' && right === 0) throw new Error('Division by zero');
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
      if (this.text[this.index] !== ')') throw new Error('Missing closing parenthesis');
      this.index += 1;
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

  parseNumber() {
    this.skipWhitespace();
    const match = this.text.slice(this.index).match(/^(?:\d+(?:\.\d*)?|\.\d+)/);
    if (!match) throw new Error('Expected number');
    this.index += match[0].length;
    return Number(match[0]);
  }
}
