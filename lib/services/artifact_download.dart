import 'dart:convert';
import 'dart:typed_data';

import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../models/chat_artifact.dart';
import '../util/markdown_table.dart';
import 'platform/artifact_platform.dart' as platform;

/// A downloadable format for an artifact. Which of these are actually offered
/// for a given artifact comes from the backend's `downloads` wire field (see
/// `ChatArtifact.downloads` / `ArtifactEvent.downloads` in `chat_service.py`),
/// read via [ArtifactDownloader.formatsFor] - not a hardcoded per-kind list.
enum DownloadFormat { svg, png, pdf, markdown, mmd }

/// A resolved filename + MIME type for a download.
class DownloadSpec {
  const DownloadSpec(this.filename, this.mime);
  final String filename;
  final String mime;

  @override
  bool operator ==(Object other) =>
      other is DownloadSpec && other.filename == filename && other.mime == mime;

  @override
  int get hashCode => Object.hash(filename, mime);

  @override
  String toString() => 'DownloadSpec($filename, $mime)';
}

/// Generates downloadable bytes for chat artifacts entirely client-side and,
/// on the web, triggers the browser download.
///
/// The byte-builders (and the filename/MIME selection) are pure and static so
/// they are unit-testable on the Dart VM without a browser; only the final
/// hand-off ([platform.downloadBytes]) and PNG rasterization touch browser APIs.
class ArtifactDownloader {
  const ArtifactDownloader();

  /// The download options offered for [artifact], in menu order - read
  /// directly from the backend's `artifact.downloads` list rather than a
  /// second, hand-maintained per-kind list (that list used to be keyed off
  /// `isDiagram` with its own order and was missing the `.mmd` format
  /// entirely - a silent drift from the backend's actual `downloads` field
  /// that nothing caught). Any entry this client build doesn't recognise is
  /// silently skipped (see [_formatFromWire]) so an unrecognised future
  /// backend format degrades gracefully instead of crashing the menu.
  static List<DownloadFormat> formatsFor(ChatArtifact artifact) {
    final hasSvg = artifact.hasSvg;
    final formats = <DownloadFormat>[];
    for (final key in artifact.downloads) {
      final format = _formatFromWire(key);
      if (format == null) continue;
      // SVG and PNG can only be produced from a pre-rendered SVG. In prod,
      // server-side Mermaid rendering is OFF, so `artifact.svg` is null and
      // both `svgBytes` and `rasterizeSvgToPng('')` would throw the moment the
      // user picked them - offering an option that is guaranteed to fail (and
      // then show a misleading error snackbar). Hide them unless an SVG is
      // actually present; the backend still advertises them in `downloads` for
      // the server-rendered path.
      if ((format == DownloadFormat.svg || format == DownloadFormat.png) &&
          !hasSvg) {
        continue;
      }
      formats.add(format);
    }
    return formats;
  }

  /// Maps one of the backend's wire download-format keys (see
  /// `ArtifactEvent.downloads` in `chat_service.py`) to a [DownloadFormat].
  /// Returns `null` for a key this client build doesn't (yet) know how to
  /// render.
  static DownloadFormat? _formatFromWire(String key) {
    switch (key) {
      case 'pdf':
        return DownloadFormat.pdf;
      case 'svg':
        return DownloadFormat.svg;
      case 'png':
        return DownloadFormat.png;
      case 'md':
        return DownloadFormat.markdown;
      case 'mmd':
        return DownloadFormat.mmd;
      default:
        return null;
    }
  }

  /// Filename stem derived from the artifact title, or a kind-based default.
  static String baseName(ChatArtifact artifact) {
    final title = artifact.title?.trim();
    final raw = (title != null && title.isNotEmpty)
        ? title
        : (artifact.isDiagram ? 'diagram' : 'code-review');
    return _slug(raw);
  }

  static String _slug(String input) {
    final cleaned = input
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'(^-+)|(-+$)'), '');
    return cleaned.isEmpty ? 'artifact' : cleaned;
  }

  /// Resolve the filename + MIME type for [artifact] in [format].
  static DownloadSpec spec(ChatArtifact artifact, DownloadFormat format) {
    final base = baseName(artifact);
    switch (format) {
      case DownloadFormat.svg:
        return DownloadSpec('$base.svg', 'image/svg+xml');
      case DownloadFormat.png:
        return DownloadSpec('$base.png', 'image/png');
      case DownloadFormat.pdf:
        return DownloadSpec('$base.pdf', 'application/pdf');
      case DownloadFormat.markdown:
        return DownloadSpec('$base.md', 'text/markdown');
      case DownloadFormat.mmd:
        // No registered MIME type for Mermaid source; plain text so any
        // browser/OS opens the saved file without complaint.
        return DownloadSpec('$base.mmd', 'text/plain');
    }
  }

  /// Human label for a format, used in the download menu.
  static String label(DownloadFormat format) {
    switch (format) {
      case DownloadFormat.svg:
        return 'SVG';
      case DownloadFormat.png:
        return 'PNG';
      case DownloadFormat.pdf:
        return 'PDF';
      case DownloadFormat.markdown:
        return 'Markdown';
      case DownloadFormat.mmd:
        return 'Mermaid source';
    }
  }

  // --- pure byte-builders (unit-testable on the VM) ------------------------

  /// The raw SVG bytes. Throws if the artifact carries no SVG.
  static Uint8List svgBytes(ChatArtifact artifact) {
    final svg = artifact.svg;
    if (svg == null || svg.trim().isEmpty) {
      throw StateError('This diagram has no pre-rendered SVG to download.');
    }
    return Uint8List.fromList(utf8.encode(svg));
  }

  /// The Markdown bytes (falls back to the mermaid source if no markdown body).
  static Uint8List markdownBytes(ChatArtifact artifact) {
    final body = artifact.markdown ?? artifact.source ?? '';
    return Uint8List.fromList(utf8.encode(body));
  }

  /// The raw Mermaid source bytes (for the `.mmd` download). Throws if the
  /// artifact carries no source text.
  static Uint8List sourceBytes(ChatArtifact artifact) {
    final source = artifact.source;
    if (source == null || source.trim().isEmpty) {
      throw StateError('This diagram has no source text to download.');
    }
    return Uint8List.fromList(utf8.encode(source));
  }

  /// Build a PDF for a code-review / markdown artifact.
  static Future<Uint8List> codeReviewPdf(ChatArtifact artifact) async {
    final body = artifact.markdown ?? artifact.source ?? '';
    final doc = pw.Document();
    doc.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(36),
        build: (context) => _markdownToWidgets(body),
      ),
    );
    return doc.save();
  }

  /// Build a PDF for a diagram: embed the SVG when present, otherwise typeset
  /// the Mermaid source so the download is never empty.
  static Future<Uint8List> diagramPdf(ChatArtifact artifact) async {
    final doc = pw.Document();
    if (artifact.hasSvg) {
      doc.addPage(
        pw.Page(
          pageFormat: PdfPageFormat.a4.landscape,
          margin: const pw.EdgeInsets.all(24),
          build: (context) =>
              pw.Center(child: pw.SvgImage(svg: artifact.svg!)),
        ),
      );
    } else {
      final source = artifact.source ?? '';
      doc.addPage(
        pw.MultiPage(
          pageFormat: PdfPageFormat.a4,
          margin: const pw.EdgeInsets.all(36),
          build: (context) => [
            pw.Text('Mermaid diagram source',
                style: pw.TextStyle(
                    fontSize: 14, fontWeight: pw.FontWeight.bold)),
            pw.SizedBox(height: 12),
            pw.Text(source,
                style: pw.TextStyle(font: pw.Font.courier(), fontSize: 9)),
          ],
        ),
      );
    }
    return doc.save();
  }

  /// A minimal Markdown-to-PDF renderer: headings, bullet lists, fenced code
  /// blocks and paragraphs. Deliberately small - it covers the shapes the
  /// code-review skill emits without pulling a full Markdown engine.
  static List<pw.Widget> _markdownToWidgets(String markdown) {
    final widgets = <pw.Widget>[];
    final lines = const LineSplitter().convert(markdown);
    final code = <String>[];
    var inCode = false;

    void flushCode() {
      if (code.isEmpty) return;
      widgets.add(
        pw.Container(
          width: double.infinity,
          padding: const pw.EdgeInsets.all(8),
          margin: const pw.EdgeInsets.symmetric(vertical: 6),
          decoration: const pw.BoxDecoration(color: PdfColor(0.95, 0.95, 0.96)),
          child: pw.Text(code.join('\n'),
              style: pw.TextStyle(font: pw.Font.courier(), fontSize: 9)),
        ),
      );
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
      // Markdown pipe-table (e.g. the code-review Findings table). Without this
      // the raw `| ERROR | ... |` and `|---|` rows would land in the PDF as
      // literal pipe text.
      if (tableStartsAt(lines, i)) {
        final table = parseTable(lines, i);
        widgets.add(_pdfTable(table.rows));
        i = table.endExclusive - 1;
        continue;
      }
      if (line.startsWith('### ')) {
        widgets.add(pw.Padding(
          padding: const pw.EdgeInsets.only(top: 8, bottom: 2),
          child: pw.Text(line.substring(4),
              style: pw.TextStyle(fontSize: 12, fontWeight: pw.FontWeight.bold)),
        ));
      } else if (line.startsWith('## ')) {
        widgets.add(pw.Padding(
          padding: const pw.EdgeInsets.only(top: 10, bottom: 3),
          child: pw.Text(line.substring(3),
              style: pw.TextStyle(fontSize: 14, fontWeight: pw.FontWeight.bold)),
        ));
      } else if (line.startsWith('# ')) {
        widgets.add(pw.Padding(
          padding: const pw.EdgeInsets.only(top: 12, bottom: 4),
          child: pw.Text(line.substring(2),
              style: pw.TextStyle(fontSize: 18, fontWeight: pw.FontWeight.bold)),
        ));
      } else if (line.trimLeft().startsWith('- ') ||
          line.trimLeft().startsWith('* ')) {
        final text = line.trimLeft().substring(2);
        widgets.add(pw.Padding(
          padding: const pw.EdgeInsets.only(left: 12, top: 1, bottom: 1),
          child: pw.Bullet(text: text, style: const pw.TextStyle(fontSize: 11)),
        ));
      } else if (line.trim().isEmpty) {
        widgets.add(pw.SizedBox(height: 6));
      } else {
        widgets.add(pw.Padding(
          padding: const pw.EdgeInsets.symmetric(vertical: 1),
          child: pw.Text(line, style: const pw.TextStyle(fontSize: 11)),
        ));
      }
    }
    flushCode();
    if (widgets.isEmpty) {
      widgets.add(pw.Text('(empty document)',
          style: const pw.TextStyle(fontSize: 11)));
    }
    return widgets;
  }

  /// Render a parsed Markdown table into a bordered PDF table (header row
  /// emphasised). Rows are padded to the header's column count so a ragged row
  /// never throws.
  static pw.Widget _pdfTable(List<List<String>> rows) {
    if (rows.isEmpty) return pw.SizedBox();
    final columns = rows.first.length;
    List<String> pad(List<String> row) => [
          for (var i = 0; i < columns; i++) i < row.length ? row[i] : '',
        ];
    final header = pad(rows.first);
    final body = rows.skip(1).map(pad).toList();

    pw.Widget cell(String text, {bool bold = false}) => pw.Padding(
          padding: const pw.EdgeInsets.all(4),
          child: pw.Text(
            text,
            style: pw.TextStyle(
              fontSize: 10,
              fontWeight: bold ? pw.FontWeight.bold : pw.FontWeight.normal,
            ),
          ),
        );

    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(vertical: 6),
      child: pw.Table(
        border: pw.TableBorder.all(
            color: const PdfColor(0.7, 0.7, 0.72), width: 0.5),
        children: [
          pw.TableRow(
            decoration: const pw.BoxDecoration(
                color: PdfColor(0.93, 0.93, 0.95)),
            children: [for (final c in header) cell(c, bold: true)],
          ),
          for (final row in body)
            pw.TableRow(children: [for (final c in row) cell(c)]),
        ],
      ),
    );
  }

  // --- orchestration -------------------------------------------------------

  /// Produce the bytes for [artifact] in [format]. PNG is web-only (it needs a
  /// canvas) and delegates to the platform seam.
  Future<Uint8List> bytesFor(ChatArtifact artifact, DownloadFormat format) {
    switch (format) {
      case DownloadFormat.svg:
        return Future.value(svgBytes(artifact));
      case DownloadFormat.markdown:
        return Future.value(markdownBytes(artifact));
      case DownloadFormat.mmd:
        return Future.value(sourceBytes(artifact));
      case DownloadFormat.pdf:
        return artifact.isDiagram ? diagramPdf(artifact) : codeReviewPdf(artifact);
      case DownloadFormat.png:
        return platform.rasterizeSvgToPng(artifact.svg ?? '');
    }
  }

  /// Generate and download [artifact] in [format] (web build only).
  Future<void> download(ChatArtifact artifact, DownloadFormat format) async {
    final bytes = await bytesFor(artifact, format);
    final s = spec(artifact, format);
    platform.downloadBytes(s.filename, s.mime, bytes);
  }
}
