/**
 * cssSelectorToXPath
 * Translates a CSS selector into an equivalent XPath 1.0 expression.
 *
 * Why this exists: the SnowScrape backend job runner only evaluates
 * xpath/regex/jsonpath (see backend/crawl_manager.py). The Visual and AI job
 * builders used to relabel a `css` field's type to `xpath` while leaving the
 * query string in CSS syntax, so at scrape time the XPath engine evaluated a
 * CSS-syntax expression and silently extracted nothing (issue #26). This
 * converter lets a CSS field actually run by emitting a real XPath string.
 *
 * It is deliberately CONSERVATIVE: it translates the common, unambiguous subset
 * of CSS and returns `null` for anything it cannot prove it translates
 * correctly (sibling combinators, pseudo-classes/elements, escapes, quote
 * characters that would break an XPath 1.0 string literal, etc.). Callers treat
 * `null` as "cannot translate" and surface a loud error rather than shipping a
 * silently-wrong query.
 *
 * Supported:
 *   - selector lists:           `a, b`            -> `xpathA | xpathB`
 *   - descendant combinator:    `div a`           -> `//div//a`
 *   - child combinator:         `div > a`         -> `//div/a`
 *   - type / universal:         `div`, `*`
 *   - id / class:               `#id`, `.class`
 *   - attribute presence/match: `[a]`, `[a=v]`, `[a^=v]`, `[a$=v]`,
 *                               `[a*=v]`, `[a~=v]`, `[a|=v]` (value optionally
 *                               quoted with " or ')
 *
 * Not supported (returns null): sibling combinators (`+`, `~`), pseudo
 * (`:hover`, `::before`, `:nth-child`), namespaces, CSS escapes (`\`), and any
 * value containing a single quote (no safe XPath 1.0 literal escape).
 */

interface Combinator {
  /** ' ' = descendant, '>' = child. The first compound has combinator ' '. */
  combinator: ' ' | '>';
  compound: string;
}

// id / class values: a CSS ident (may start with a single leading hyphen).
const IDENT = /^-?[A-Za-z_][\w-]*$/;
// element and attribute NAMES: no leading hyphen (a bare `//-div` / `@-foo` name
// test is invalid XPath). HTML lowercases these at parse time, so we lowercase
// before emitting; XPath name tests are case-sensitive (see issue #26 review).
const NAME_TOKEN = /^[A-Za-z_][\w-]*$/;

/** Split a string on a delimiter, ignoring delimiters inside [] or quotes. */
function splitTopLevel(input: string, delim: string): string[] | null {
  const parts: string[] = [];
  let buf = '';
  let depth = 0;
  let quote: string | null = null;
  for (let i = 0; i < input.length; i++) {
    const ch = input[i];
    if (quote) {
      if (ch === quote) quote = null;
      buf += ch;
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
      buf += ch;
      continue;
    }
    if (ch === '[') depth++;
    else if (ch === ']') depth--;
    if (depth === 0 && ch === delim) {
      parts.push(buf);
      buf = '';
      continue;
    }
    buf += ch;
  }
  if (quote || depth !== 0) return null; // unbalanced
  parts.push(buf);
  return parts;
}

/**
 * Break one complex selector into its compound selectors and the combinators
 * between them. Returns null on an unsupported combinator (`+`, `~`).
 */
function tokenizeComplex(group: string): Combinator[] | null {
  const tokens: Combinator[] = [];
  let buf = '';
  let depth = 0;
  let quote: string | null = null;
  // combinator that precedes the NEXT compound we flush; first one is ' '.
  let pending: ' ' | '>' = ' ';
  let sawCombinatorChar = false;

  const flush = (): boolean => {
    if (buf.trim()) {
      tokens.push({ combinator: pending, compound: buf.trim() });
      buf = '';
      pending = ' ';
      sawCombinatorChar = false;
    }
    return true;
  };

  for (let i = 0; i < group.length; i++) {
    const ch = group[i];
    if (quote) {
      if (ch === quote) quote = null;
      buf += ch;
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
      buf += ch;
      continue;
    }
    if (ch === '[') depth++;
    else if (ch === ']') depth--;

    if (depth === 0 && (ch === ' ' || ch === '\t' || ch === '\n')) {
      flush();
      continue;
    }
    if (depth === 0 && ch === '>') {
      flush();
      if (sawCombinatorChar) return null; // e.g. `a > > b`
      pending = '>';
      sawCombinatorChar = true;
      continue;
    }
    if (depth === 0 && (ch === '+' || ch === '~')) {
      return null; // sibling combinators not supported
    }
    buf += ch;
  }
  if (quote || depth !== 0) return null;
  flush();
  // A dangling combinator with no following compound (e.g. `div >`) is invalid.
  if (sawCombinatorChar) return null;
  return tokens.length ? tokens : null;
}

/** Build an XPath 1.0 string literal, or null if the value cannot be safely quoted. */
function xpathLiteral(value: string): string | null {
  if (value.includes("'")) return null; // XPath 1.0 has no literal escape; bail
  return `'${value}'`;
}

/** Translate one attribute selector body (without the surrounding []). */
function translateAttribute(body: string): string | null {
  // The operator is the first `=` outside quotes (the name has no quotes and no
  // `=`, so the first `=` always marks the operator: =, ^=, $=, *=, ~=, |=).
  let eq = -1;
  let quote: string | null = null;
  for (let i = 0; i < body.length; i++) {
    const c = body[i];
    if (quote) {
      if (c === quote) quote = null;
    } else if (c === '"' || c === "'") {
      quote = c;
    } else if (c === '=') {
      eq = i;
      break;
    }
  }

  if (eq === -1) {
    // presence: [attr]
    const name = body.trim();
    if (!NAME_TOKEN.test(name)) return null;
    return `@${name.toLowerCase()}`;
  }

  const opChar = eq > 0 ? body[eq - 1] : '';
  let op: string;
  let rawName: string;
  if (opChar === '^' || opChar === '$' || opChar === '*' || opChar === '~' || opChar === '|') {
    op = `${opChar}=`;
    rawName = body.slice(0, eq - 1).trim();
  } else {
    op = '=';
    rawName = body.slice(0, eq).trim();
  }
  let rawVal = body.slice(eq + 1);
  if (!NAME_TOKEN.test(rawName)) return null;
  // HTML lowercases attribute names; XPath name tests are case-sensitive.
  const name = rawName.toLowerCase();

  rawVal = rawVal.trim();
  // strip matching quotes
  if (
    rawVal.length >= 2 &&
    (rawVal[0] === '"' || rawVal[0] === "'") &&
    rawVal[rawVal.length - 1] === rawVal[0]
  ) {
    rawVal = rawVal.slice(1, -1);
  }
  if (rawVal.includes('\\')) return null; // CSS escapes not handled

  const lit = xpathLiteral(rawVal);
  if (lit === null) return null;

  // Per CSS, the substring/prefix/suffix/word/hyphen operators NEVER match an
  // empty value, but the naive XPath (e.g. contains(@x,'')) matches every
  // element with the attribute. Bail to null so the builder fails loudly rather
  // than silently matching everything. Exact `=` with an empty value is fine.
  if (op !== '=' && rawVal === '') return null;

  switch (op) {
    case '=':
      return `@${name}=${lit}`;
    case '^=':
      return `starts-with(@${name},${lit})`;
    case '$=':
      return `substring(@${name},string-length(@${name})-string-length(${lit})+1)=${lit}`;
    case '*=':
      return `contains(@${name},${lit})`;
    case '~=': {
      // whitespace-separated word match
      const wordLit = xpathLiteral(` ${rawVal} `);
      if (wordLit === null) return null;
      return `contains(concat(' ',normalize-space(@${name}),' '),${wordLit})`;
    }
    case '|=': {
      // exactly val, or val followed by a hyphen
      const dashLit = xpathLiteral(`${rawVal}-`);
      if (dashLit === null) return null;
      return `(@${name}=${lit} or starts-with(@${name},${dashLit}))`;
    }
    default:
      return null;
  }
}

/** Translate a compound selector (no combinators) into an XPath step. */
function translateCompound(compound: string): string | null {
  let element = '';
  const predicates: string[] = [];
  let i = 0;

  // optional type / universal selector at the start
  if (compound[0] === '*') {
    element = '*';
    i = 1;
  } else if (compound[0] && compound[0] !== '#' && compound[0] !== '.' && compound[0] !== '[') {
    let tag = '';
    while (i < compound.length && /[\w-]/.test(compound[i])) {
      tag += compound[i];
      i++;
    }
    if (!NAME_TOKEN.test(tag)) return null;
    // HTML lowercases element names; XPath name tests are case-sensitive.
    element = tag.toLowerCase();
  }

  while (i < compound.length) {
    const ch = compound[i];
    if (ch === '#') {
      i++;
      let id = '';
      while (i < compound.length && /[\w-]/.test(compound[i])) {
        id += compound[i];
        i++;
      }
      if (!IDENT.test(id)) return null;
      const lit = xpathLiteral(id);
      if (lit === null) return null;
      predicates.push(`@id=${lit}`);
    } else if (ch === '.') {
      i++;
      let cls = '';
      while (i < compound.length && /[\w-]/.test(compound[i])) {
        cls += compound[i];
        i++;
      }
      if (!IDENT.test(cls)) return null;
      const wordLit = xpathLiteral(` ${cls} `);
      if (wordLit === null) return null;
      predicates.push(`contains(concat(' ',normalize-space(@class),' '),${wordLit})`);
    } else if (ch === '[') {
      // find matching ] respecting quotes
      let j = i + 1;
      let quote: string | null = null;
      let body = '';
      let closed = false;
      while (j < compound.length) {
        const c = compound[j];
        if (quote) {
          if (c === quote) quote = null;
          body += c;
        } else if (c === '"' || c === "'") {
          quote = c;
          body += c;
        } else if (c === ']') {
          closed = true;
          break;
        } else {
          body += c;
        }
        j++;
      }
      if (!closed) return null;
      const attr = translateAttribute(body);
      if (attr === null) return null;
      predicates.push(attr);
      i = j + 1;
    } else if (ch === ':') {
      return null; // pseudo-classes / pseudo-elements unsupported
    } else {
      return null; // unexpected character
    }
  }

  if (!element) element = '*';
  if (predicates.length === 0) return element;
  return `${element}[${predicates.join(' and ')}]`;
}

/** Translate one complex selector (a single member of the selector list). */
function translateComplex(group: string): string | null {
  const tokens = tokenizeComplex(group);
  if (!tokens) return null;
  let xpath = '';
  for (let k = 0; k < tokens.length; k++) {
    const { combinator, compound } = tokens[k];
    const step = translateCompound(compound);
    if (step === null) return null;
    if (k === 0) {
      xpath = `//${step}`;
    } else {
      xpath += combinator === '>' ? `/${step}` : `//${step}`;
    }
  }
  return xpath;
}

/**
 * Convert a CSS selector to an equivalent XPath 1.0 expression.
 * Returns null when the selector uses a feature this converter cannot translate
 * faithfully; callers should treat null as "not translatable".
 */
export function cssSelectorToXPath(selector: string): string | null {
  if (typeof selector !== 'string') return null;
  const trimmed = selector.trim();
  if (!trimmed) return null;
  // An expression that already looks like XPath is not CSS; do not touch it.
  if (trimmed.startsWith('/') || trimmed.startsWith('(')) return null;

  const groups = splitTopLevel(trimmed, ',');
  if (!groups) return null;

  const xpaths: string[] = [];
  for (const group of groups) {
    const g = group.trim();
    if (!g) return null; // empty member, e.g. trailing comma
    const xp = translateComplex(g);
    if (xp === null) return null;
    xpaths.push(xp);
  }
  return xpaths.join(' | ');
}
