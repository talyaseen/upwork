/// Shared GitHub-Flavored-Markdown pipe-table parsing, used by BOTH the live
/// artifact view and the PDF export so the two renderers agree exactly on what
/// counts as a table. Keeping a single source here means a parsing fix (e.g.
/// the false-positive guard below) lands once instead of drifting between the
/// two copies.
library;

/// A parsed Markdown table: [rows] (header first) plus the exclusive index of
/// the first line after the table, so the caller can advance past it.
class ParsedMarkdownTable {
  const ParsedMarkdownTable(this.rows, this.endExclusive);
  final List<List<String>> rows;
  final int endExclusive;
}

/// True when a GFM pipe-table begins at [index]: a header row that contains a
/// pipe, immediately followed by a separator row (see [isTableSeparator]).
bool tableStartsAt(List<String> lines, int index) {
  if (index + 1 >= lines.length) return false;
  final header = lines[index];
  if (!header.contains('|') || header.trim().isEmpty) return false;
  return isTableSeparator(
    lines[index + 1],
    headerCellCount: tableCells(header).length,
  );
}

/// Split a Markdown table row into trimmed cells, dropping the empty cells that
/// leading/trailing pipes create.
List<String> tableCells(String line) {
  var s = line.trim();
  if (s.startsWith('|')) s = s.substring(1);
  if (s.endsWith('|')) s = s.substring(0, s.length - 1);
  return s.split('|').map((c) => c.trim()).toList();
}

/// A separator row is all dash/colon cells (e.g. `|---|:--:|`), contains at
/// least one pipe, AND has exactly [headerCellCount] cells (per the GFM spec).
///
/// The pipe and column-count requirements together stop a plain prose line that
/// happens to contain a `|` and is followed by a bare `---` horizontal rule
/// from being mis-read as a one-column table - which previously swallowed the
/// following text in both the live view and the PDF.
bool isTableSeparator(String line, {required int headerCellCount}) {
  if (!line.contains('|')) return false;
  final cells = tableCells(line);
  if (cells.isEmpty || cells.length != headerCellCount) return false;
  final cell = RegExp(r'^:?-{1,}:?$');
  return cells.every((c) => cell.hasMatch(c));
}

/// Parse the table starting at [index] (header + separator + body rows).
ParsedMarkdownTable parseTable(List<String> lines, int index) {
  final rows = <List<String>>[tableCells(lines[index])];
  var j = index + 2; // skip header + separator
  while (j < lines.length &&
      lines[j].contains('|') &&
      lines[j].trim().isNotEmpty &&
      !lines[j].trimLeft().startsWith('```')) {
    rows.add(tableCells(lines[j]));
    j++;
  }
  return ParsedMarkdownTable(rows, j);
}
