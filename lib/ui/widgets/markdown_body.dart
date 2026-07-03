import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../util/markdown_table.dart';

/// Remove ```` ```mermaid ... ``` ```` fenced blocks from [markdown].
///
/// Used to drop the duplicative raw Mermaid source from an assistant message
/// body when the same message already renders that diagram as its own card
/// artifact below the text: the model tends to echo the ```` ```mermaid ````
/// source into the prose AND emit it as an artifact, so without this the reader
/// sees the same diagram source twice (once as literal code, once rendered).
///
/// Only the fenced Mermaid block is removed; every other line (surrounding
/// prose, other code fences, tables) is left byte-for-byte intact. A run of
/// blank lines the removal leaves behind is collapsed so the prose does not
/// grow a visible gap where the block used to be.
String stripMermaidFences(String markdown) {
  final lines = markdown.split('\n');
  final out = <String>[];
  final open = RegExp(r'^`{3,}\s*mermaid\b', caseSensitive: false);
  var inMermaid = false;
  for (final line in lines) {
    final trimmed = line.trimLeft();
    if (!inMermaid) {
      if (open.hasMatch(trimmed)) {
        inMermaid = true;
        continue;
      }
      out.add(line);
      continue;
    }
    // Inside the mermaid block: swallow every line up to and including the
    // closing fence.
    if (trimmed.startsWith('```')) inMermaid = false;
  }
  return out
      .join('\n')
      .replaceAll(RegExp(r'\n{3,}'), '\n\n')
      .trim();
}

/// A small, dependency-free Markdown renderer shared by the inline artifact
/// card (a code-review / markdown document) and the assistant message body, so
/// the two render identically: headings (`#`/`##`/`###`), GFM pipe-tables
/// (via [markdown_table]), fenced code blocks, bullet lists, and inline
/// `**bold**` + `` `code` `` emphasis.
///
/// [boxed] wraps the content in the bordered, tinted panel used by the artifact
/// card; the message body sets it false because it already sits inside a chat
/// bubble surface and a second nested box would read as a card-in-a-card.
class MarkdownBody extends StatelessWidget {
  const MarkdownBody({
    super.key,
    required this.markdown,
    this.boxed = true,
    this.paragraphSize = 13.5,
  });

  final String markdown;
  final bool boxed;

  /// Font size for ordinary paragraph + list text. The artifact card renders a
  /// dense document at the default 13.5; the chat message body passes its
  /// conversational body size (14.5) so normal answers keep their established
  /// reading size and only the structured elements (headings, tables, code)
  /// change. Headings scale off their own absolute sizes regardless.
  final double paragraphSize;

  @override
  Widget build(BuildContext context) {
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: _blocks(),
    );
    if (!boxed) return content;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppTheme.spaceMd),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        border: Border.all(color: AppTheme.border),
      ),
      child: content,
    );
  }

  List<Widget> _blocks() {
    final lines = markdown.split('\n');
    final spans = <Widget>[];
    final code = <String>[];
    var inCode = false;

    void flushCode() {
      if (code.isEmpty) return;
      spans.add(Container(
        width: double.infinity,
        margin: const EdgeInsets.symmetric(vertical: AppTheme.spaceSm - 2),
        padding: const EdgeInsets.all(AppTheme.spaceSm + 2),
        decoration: BoxDecoration(
          color: AppTheme.background,
          borderRadius: BorderRadius.circular(AppTheme.radiusSm),
          border: Border.all(color: AppTheme.border),
        ),
        child: SelectableText(code.join('\n'), style: AppTheme.mono),
      ));
      code.clear();
    }

    for (var i = 0; i < lines.length; i++) {
      final line = lines[i];
      if (line.trimLeft().startsWith('```')) {
        if (inCode) {
          flushCode();
          inCode = false;
        } else {
          inCode = true;
        }
        continue;
      }
      if (inCode) {
        code.add(line);
        continue;
      }
      // A Markdown pipe-table: a header row followed by a `|---|---|` separator.
      // The code-review skill's mandated Findings table arrives this way;
      // without this branch the `| ERROR | ... |` and `|---|` rows render as
      // literal pipe text, which reads as broken output.
      if (tableStartsAt(lines, i)) {
        final table = parseTable(lines, i);
        spans.add(_tableWidget(table.rows));
        i = table.endExclusive - 1; // -1: the for-loop ++ back to endExclusive
        continue;
      }
      spans.add(_line(line));
    }
    if (inCode) flushCode();
    return spans;
  }

  Widget _line(String line) {
    if (line.startsWith('# ')) {
      return _text(line.substring(2), size: 18, weight: FontWeight.w700);
    }
    if (line.startsWith('## ')) {
      return _text(line.substring(3), size: 15.5, weight: FontWeight.w700);
    }
    if (line.startsWith('### ')) {
      return _text(line.substring(4), size: 14, weight: FontWeight.w700);
    }
    if (line.trimLeft().startsWith('- ') || line.trimLeft().startsWith('* ')) {
      final t = line.trimLeft().substring(2);
      return Padding(
        padding: const EdgeInsets.only(left: 8, top: 1, bottom: 1),
        child: _text('•  $t', size: paragraphSize),
      );
    }
    if (line.trim().isEmpty) return const SizedBox(height: 6);
    return _text(line, size: paragraphSize);
  }

  Widget _text(String t, {required double size, FontWeight? weight}) {
    final base = TextStyle(
      color: AppTheme.textPrimary,
      fontSize: size,
      height: 1.45,
      fontWeight: weight ?? FontWeight.w400,
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1.5),
      child: SelectableText.rich(
        TextSpan(children: _inline(t, base)),
        style: base,
      ),
    );
  }

  /// Split a single line into inline spans, honouring `**bold**` and
  /// `` `inline code` ``. Everything else is emitted verbatim, so a line with
  /// no emphasis produces exactly one span carrying the whole line.
  List<InlineSpan> _inline(String text, TextStyle base) {
    final spans = <InlineSpan>[];
    // Bold first (group 1), then inline code (group 2). Non-greedy so adjacent
    // runs don't merge.
    final re = RegExp(r'\*\*(.+?)\*\*|`([^`]+)`');
    var last = 0;
    for (final m in re.allMatches(text)) {
      if (m.start > last) {
        spans.add(TextSpan(text: text.substring(last, m.start), style: base));
      }
      final bold = m.group(1);
      if (bold != null) {
        spans.add(TextSpan(
          text: bold,
          style: base.copyWith(fontWeight: FontWeight.w700),
        ));
      } else {
        spans.add(TextSpan(
          text: m.group(2),
          style: base.copyWith(
            fontFamily: AppTheme.monoFontFamily,
            background: Paint()..color = AppTheme.background,
          ),
        ));
      }
      last = m.end;
    }
    if (last < text.length) {
      spans.add(TextSpan(text: text.substring(last), style: base));
    }
    if (spans.isEmpty) spans.add(TextSpan(text: text, style: base));
    return spans;
  }

  Widget _tableWidget(List<List<String>> rows) {
    if (rows.isEmpty) return const SizedBox.shrink();
    final columns = rows.first.length;
    List<String> pad(List<String> row) => [
          for (var i = 0; i < columns; i++) i < row.length ? row[i] : '',
        ];
    final header = pad(rows.first);
    final body = rows.skip(1).map(pad).toList();

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(vertical: AppTheme.spaceSm),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppTheme.radiusSm),
        border: Border.all(color: AppTheme.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: Table(
        border: TableBorder.symmetric(
          inside: const BorderSide(color: AppTheme.border),
        ),
        defaultVerticalAlignment: TableCellVerticalAlignment.middle,
        children: [
          TableRow(
            decoration: const BoxDecoration(color: AppTheme.surfaceRaised),
            children: [for (final cell in header) _tableCell(cell, header: true)],
          ),
          for (final row in body)
            TableRow(
              children: [for (final cell in row) _tableCell(cell)],
            ),
        ],
      ),
    );
  }

  Widget _tableCell(String text, {bool header = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      child: SelectableText(
        text,
        style: TextStyle(
          color: AppTheme.textPrimary,
          fontSize: 12.5,
          height: 1.35,
          fontWeight: header ? FontWeight.w700 : FontWeight.w400,
        ),
      ),
    );
  }
}
