import 'package:flutter_ai_chat/models/citation.dart';
import 'package:flutter_test/flutter_test.dart';

// The backend HTML-escapes citation titles and passage text. A Flutter Text is
// not an HTML sink, so Citation.fromJson must un-escape the entities; otherwise
// every card quoting a phrase with an apostrophe or ampersand shows raw
// entities and the flagship "check the sources" feature looks corrupted.

Citation _fromWire({String? title, String? text}) => Citation.fromJson({
      'document_id': 1,
      'document_title': title ?? 'Doc',
      'chunk_id': 2,
      'text': text ?? 'body',
      'score': 0.9,
    });

void main() {
  group('Citation.fromJson un-escapes HTML entities', () {
    // REGRESSION PIN (H3): before the fix these rendered verbatim as `&#x27;`
    // and `&amp;` in the citation card.
    test('a hex numeric apostrophe entity is decoded', () {
      final c = _fromWire(text: 'It&#x27;s grounded');
      expect(c.text, "It's grounded");
      expect(c.text, isNot(contains('&#x27;')));
    });

    test('a decimal numeric apostrophe entity is decoded', () {
      final c = _fromWire(text: 'It&#39;s grounded');
      expect(c.text, "It's grounded");
    });

    test('named ampersand/lt/gt/quot entities are decoded', () {
      final c = _fromWire(
        title: 'Auth &amp; Sessions',
        text: '&lt;tag&gt; &quot;quoted&quot;',
      );
      expect(c.documentTitle, 'Auth & Sessions');
      expect(c.text, '<tag> "quoted"');
    });

    test('combined ampersand + apostrophe in one string decodes fully', () {
      // The backend escapes `&` first, so `it's & more` -> `it&#x27;s &amp; more`.
      final c = _fromWire(text: 'it&#x27;s &amp; more');
      expect(c.text, "it's & more");
    });

    test('plain text with no entities passes through untouched', () {
      final c = _fromWire(title: 'Plain Title', text: 'nothing to decode here');
      expect(c.documentTitle, 'Plain Title');
      expect(c.text, 'nothing to decode here');
    });

    test('an unknown entity is left as-is rather than dropped', () {
      final c = _fromWire(text: 'keep &notareal; intact');
      expect(c.text, 'keep &notareal; intact');
    });

    test('a bare ampersand (not an entity) is preserved', () {
      final c = _fromWire(text: 'AT&T style');
      expect(c.text, 'AT&T style');
    });

    // REGRESSION PIN: a numeric entity above the Unicode maximum (0x10FFFF)
    // made String.fromCharCode throw a RangeError, crashing the decoder for
    // the whole citation. It must now fall through to a harmless passthrough.
    test('an out-of-range numeric entity is left intact, never throws', () {
      final hex = _fromWire(text: 'oops &#x110000; here'); // 0x110000 > max
      expect(hex.text, 'oops &#x110000; here');
      final dec = _fromWire(text: 'oops &#9999999; here'); // > 0x10FFFF
      expect(dec.text, 'oops &#9999999; here');
    });
  });
}
