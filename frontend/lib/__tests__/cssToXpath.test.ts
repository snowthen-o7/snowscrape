import { describe, it, expect } from 'vitest';
import { cssSelectorToXPath } from '@/lib/jobs/cssToXpath';

describe('cssSelectorToXPath', () => {
  describe('simple selectors', () => {
    it('translates a type selector', () => {
      expect(cssSelectorToXPath('div')).toBe('//div');
    });

    it('translates the universal selector', () => {
      expect(cssSelectorToXPath('*')).toBe('//*');
    });

    it('translates an id selector (implicit universal element)', () => {
      expect(cssSelectorToXPath('#main')).toBe("//*[@id='main']");
    });

    it('translates a class selector with whitespace-safe matching', () => {
      expect(cssSelectorToXPath('.price')).toBe(
        "//*[contains(concat(' ',normalize-space(@class),' '),' price ')]"
      );
    });

    it('translates a type + class selector', () => {
      expect(cssSelectorToXPath('span.price')).toBe(
        "//span[contains(concat(' ',normalize-space(@class),' '),' price ')]"
      );
    });

    it('combines multiple simple selectors on one compound with `and`', () => {
      expect(cssSelectorToXPath('a.btn#cta')).toBe(
        "//a[contains(concat(' ',normalize-space(@class),' '),' btn ') and @id='cta']"
      );
    });

    it('combines multiple classes', () => {
      expect(cssSelectorToXPath('.a.b')).toBe(
        "//*[contains(concat(' ',normalize-space(@class),' '),' a ') and contains(concat(' ',normalize-space(@class),' '),' b ')]"
      );
    });
  });

  describe('attribute selectors', () => {
    it('presence', () => {
      expect(cssSelectorToXPath('[data-id]')).toBe('//*[@data-id]');
    });

    it('exact match', () => {
      expect(cssSelectorToXPath('[type=text]')).toBe("//*[@type='text']");
    });

    it('exact match with quoted value', () => {
      expect(cssSelectorToXPath('a[title="buy now"]')).toBe("//a[@title='buy now']");
    });

    it('prefix match ^=', () => {
      expect(cssSelectorToXPath('[href^=https]')).toBe("//*[starts-with(@href,'https')]");
    });

    it('suffix match $=', () => {
      expect(cssSelectorToXPath('[src$=.png]')).toBe(
        "//*[substring(@src,string-length(@src)-string-length('.png')+1)='.png']"
      );
    });

    it('substring match *=', () => {
      expect(cssSelectorToXPath('[class*=col]')).toBe("//*[contains(@class,'col')]");
    });

    it('whitespace-word match ~=', () => {
      expect(cssSelectorToXPath('[rel~=author]')).toBe(
        "//*[contains(concat(' ',normalize-space(@rel),' '),' author ')]"
      );
    });

    it('hyphen-prefix match |=', () => {
      expect(cssSelectorToXPath('[lang|=en]')).toBe(
        "//*[(@lang='en' or starts-with(@lang,'en-'))]"
      );
    });

    it('type + attribute', () => {
      expect(cssSelectorToXPath('input[type=checkbox]')).toBe("//input[@type='checkbox']");
    });
  });

  describe('combinators', () => {
    it('descendant', () => {
      expect(cssSelectorToXPath('div span')).toBe('//div//span');
    });

    it('child', () => {
      expect(cssSelectorToXPath('ul > li')).toBe('//ul/li');
    });

    it('child without surrounding spaces', () => {
      expect(cssSelectorToXPath('ul>li')).toBe('//ul/li');
    });

    it('mixed descendant and child', () => {
      expect(cssSelectorToXPath('table tr > td.amount')).toBe(
        "//table//tr/td[contains(concat(' ',normalize-space(@class),' '),' amount ')]"
      );
    });

    it('collapses repeated whitespace between compounds', () => {
      expect(cssSelectorToXPath('div    span')).toBe('//div//span');
    });
  });

  describe('selector lists', () => {
    it('joins members with the XPath union operator', () => {
      expect(cssSelectorToXPath('h1, h2')).toBe('//h1 | //h2');
    });

    it('handles complex members in a list', () => {
      expect(cssSelectorToXPath('.a, div > .b')).toBe(
        "//*[contains(concat(' ',normalize-space(@class),' '),' a ')] | //div/*[contains(concat(' ',normalize-space(@class),' '),' b ')]"
      );
    });

    it('does not split on a comma inside an attribute value', () => {
      expect(cssSelectorToXPath('[data-x="a,b"]')).toBe("//*[@data-x='a,b']");
    });
  });

  describe('returns null for untranslatable / non-CSS input', () => {
    it.each([
      ['empty string', ''],
      ['whitespace only', '   '],
      ['already an xpath', '//span[@class="price"]'],
      ['xpath starting with paren', '(//a)[1]'],
      ['adjacent sibling combinator', 'h1 + p'],
      ['general sibling combinator', 'h1 ~ p'],
      ['pseudo-class', 'a:hover'],
      ['pseudo-element', 'p::before'],
      ['nth-child', 'li:nth-child(2)'],
      ['dangling child combinator', 'div >'],
      ['double child combinator', 'a > > b'],
      ['unbalanced bracket', 'a[type=text'],
      ['value with single quote', "[title=it's]"],
      ['css escape in value', '[data-x=a\\,b]'],
      ['trailing comma', 'div,'],
      ['leading comma', ',div'],
    ])('%s', (_label, input) => {
      expect(cssSelectorToXPath(input)).toBeNull();
    });

    it('returns null for non-string input', () => {
      // @ts-expect-error exercising the runtime guard
      expect(cssSelectorToXPath(null)).toBeNull();
      // @ts-expect-error exercising the runtime guard
      expect(cssSelectorToXPath(undefined)).toBeNull();
    });
  });

  describe('trimming', () => {
    it('trims surrounding whitespace', () => {
      expect(cssSelectorToXPath('  div.card  ')).toBe(
        "//div[contains(concat(' ',normalize-space(@class),' '),' card ')]"
      );
    });
  });
});
