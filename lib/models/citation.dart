import 'package:flutter/foundation.dart';

/// A single source passage that supports an assistant answer.
///
/// Mirrors the backend `Citation` schema. Citations are what make the
/// assistant read as a grounded system rather than a toy: every answer is
/// traceable to the document and passage it came from.
@immutable
class Citation {
  const Citation({
    required this.documentId,
    required this.documentTitle,
    required this.chunkId,
    required this.text,
    required this.score,
  });

  final int documentId;
  final String documentTitle;
  final int chunkId;
  final String text;
  final double score;

  /// Relevance as a 0-100 percentage, for a compact UI badge.
  int get relevancePercent => (score.clamp(0.0, 1.0) * 100).round();

  factory Citation.fromJson(Map<String, dynamic> json) {
    return Citation(
      documentId: (json['document_id'] as num).toInt(),
      // The backend HTML-escapes the title and passage text (e.g. an apostrophe
      // becomes `&#x27;`, `&` becomes `&amp;`). A Flutter [Text] is not an HTML
      // sink - it renders the string verbatim - so without un-escaping here,
      // every citation card that quotes a phrase with an apostrophe or
      // ampersand shows raw entities like `&#x27;`/`&amp;`, making the flagship
      // "check the sources" feature look corrupted. Un-escaping is safe: the
      // result is only ever placed into a plain-text widget, never parsed as
      // markup.
      documentTitle:
          _htmlUnescape(json['document_title'] as String? ?? 'Untitled'),
      chunkId: (json['chunk_id'] as num).toInt(),
      text: _htmlUnescape(json['text'] as String? ?? ''),
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

/// Reverse HTML entity escaping applied server-side, covering the named and
/// numeric (decimal + hex) entities that appear in escaped prose. Unknown
/// entities are left untouched rather than dropped, so the worst case is a
/// harmless passthrough. The input is single-escaped by the backend, so a
/// single pass is correct.
String _htmlUnescape(String input) {
  if (!input.contains('&')) return input;
  return input.replaceAllMapped(
    RegExp(r'&(#[xX][0-9a-fA-F]+|#[0-9]+|[a-zA-Z][a-zA-Z0-9]*);'),
    (match) {
      final entity = match.group(1)!;
      if (entity.startsWith('#x') || entity.startsWith('#X')) {
        final code = int.tryParse(entity.substring(2), radix: 16);
        return _fromCharCode(code, match);
      }
      if (entity.startsWith('#')) {
        final code = int.tryParse(entity.substring(1));
        return _fromCharCode(code, match);
      }
      return _namedEntities[entity] ?? match.group(0)!;
    },
  );
}

/// Turn a decoded numeric entity [code] into its character, leaving the raw
/// match untouched when the value is missing or out of Unicode range.
/// [String.fromCharCode] throws a RangeError for any code point above the
/// Unicode maximum (0x10FFFF), so an oversized numeric entity like `&#9999999;`
/// must fall through to a harmless passthrough rather than crash the decoder.
String _fromCharCode(int? code, Match match) {
  if (code == null || code < 0 || code > 0x10FFFF) return match.group(0)!;
  return String.fromCharCode(code);
}

const Map<String, String> _namedEntities = {
  'amp': '&',
  'lt': '<',
  'gt': '>',
  'quot': '"',
  'apos': "'",
  'nbsp': ' ',
  'copy': '©',
  'reg': '®',
  'trade': '™',
  'hellip': '…',
  'mdash': '—',
  'ndash': '–',
  'lsquo': '‘',
  'rsquo': '’',
  'ldquo': '“',
  'rdquo': '”',
};
