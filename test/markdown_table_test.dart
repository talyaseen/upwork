import 'package:flutter_ai_chat/util/markdown_table.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('markdown_table shared parser', () {
    test('a real GFM pipe-table is detected and parsed', () {
      final lines = [
        '| Severity | Finding | Location |',
        '|----------|---------|----------|',
        '| ERROR | SQL injection | db.py:42 |',
        '| WARN | Missing retry | api.py:10 |',
      ];
      expect(tableStartsAt(lines, 0), isTrue);
      final parsed = parseTable(lines, 0);
      expect(parsed.rows.first, ['Severity', 'Finding', 'Location']);
      expect(parsed.rows[1], ['ERROR', 'SQL injection', 'db.py:42']);
      expect(parsed.endExclusive, 4);
    });

    test('a prose "|" line followed by a bare "---" rule is NOT a table', () {
      final lines = [
        'Use the pipe | operator to combine streams.',
        '---',
        'That rule is a divider, not a table.',
      ];
      // Bare `---` has no pipe -> not a separator -> not a table.
      expect(tableStartsAt(lines, 0), isFalse);
    });

    test('a separator whose column count differs from the header is rejected',
        () {
      final lines = [
        'text with | one pipe here',
        '|---|', // 1 cell vs header's 2 cells -> mismatch
        'more text',
      ];
      expect(isTableSeparator(lines[1], headerCellCount: 2), isFalse);
      expect(tableStartsAt(lines, 0), isFalse);
    });

    test('a matching multi-column separator with pipes is accepted', () {
      expect(isTableSeparator('|:--|--:|', headerCellCount: 2), isTrue);
      expect(isTableSeparator('---', headerCellCount: 1), isFalse);
    });
  });
}
