import 'dart:convert';

import 'package:flutter_ai_chat/models/chat_artifact.dart';
import 'package:flutter_ai_chat/services/artifact_download.dart';
import 'package:flutter_test/flutter_test.dart';

// These tests exercise the pure, client-side download builders on the Dart VM:
// filename/MIME selection and the byte/document generation. No browser, no
// network. The PNG and the actual browser save are web-only and excluded here.

// `downloads` mirrors exactly what the backend sends for each real skill (see
// `ArtifactEvent(..., downloads=[...])` in `chat_service.py`) so these
// fixtures exercise the real wire-driven format list, not a guess.
ChatArtifact _diagram({String? svg, String? title}) => ChatArtifact(
      kind: ArtifactKind.mermaid,
      title: title,
      source: 'graph TD; A-->B',
      svg: svg,
      downloads: const ['pdf', 'svg', 'png', 'mmd'],
    );

ChatArtifact _review({String? title}) => ChatArtifact(
      kind: ArtifactKind.markdown,
      title: title,
      markdown: '# Findings\n\n- The worker is not idempotent.\n\n'
          '```py\nprint("x")\n```\n',
      downloads: const ['pdf', 'md'],
    );

bool _isPdf(List<int> bytes) =>
    bytes.length > 4 &&
    bytes[0] == 0x25 && // %
    bytes[1] == 0x50 && // P
    bytes[2] == 0x44 && // D
    bytes[3] == 0x46; // F

void main() {
  group("format options come from the backend's downloads field", () {
    test(
        'a diagram WITH a pre-rendered SVG offers exactly its downloads list, '
        'in order (PDF, SVG, PNG, Mermaid source)', () {
      expect(
        ArtifactDownloader.formatsFor(_diagram(svg: '<svg/>')),
        [
          DownloadFormat.pdf,
          DownloadFormat.svg,
          DownloadFormat.png,
          DownloadFormat.mmd,
        ],
      );
    });

    // REGRESSION PIN (M5): in prod, server-side Mermaid rendering is OFF, so a
    // diagram arrives with `svg == null` even though the backend still lists
    // `svg`/`png` in `downloads`. Offering them was a guaranteed failure -
    // picking SVG threw in `svgBytes`, PNG rasterized an empty string - and the
    // UI then showed a misleading "available on the web build" snackbar to a
    // user who WAS on web. `formatsFor` must now drop svg/png when there is no
    // SVG to produce them from, while keeping the always-producible formats.
    test('a diagram with NO pre-rendered SVG hides svg/png', () {
      expect(
        ArtifactDownloader.formatsFor(_diagram()),
        [DownloadFormat.pdf, DownloadFormat.mmd],
      );
    });

    test('a code-review offers PDF (primary) then Markdown', () {
      expect(
        ArtifactDownloader.formatsFor(_review()),
        [DownloadFormat.pdf, DownloadFormat.markdown],
      );
    });

    // REGRESSION PIN: `formatsFor` used to derive its answer from
    // `artifact.isDiagram` via a second, hand-maintained list that had
    // drifted from the backend's real `downloads` field (wrong order, and
    // missing `.mmd` entirely). This mock's `downloads` list would produce a
    // DIFFERENT result under that old per-kind logic (a diagram used to
    // always get [svg, png, pdf], regardless of what the backend actually
    // sent) - proving the format list now comes from the field itself, not a
    // hardcoded per-kind assumption.
    test(
        'formatsFor reflects an arbitrary downloads list exactly - no more, '
        'no less, no hardcoded per-kind assumption', () {
      final artifact = ChatArtifact.fromJson(const {
        'kind': 'mermaid', // isDiagram == true
        'source': 'graph TD; A-->B',
        'downloads': ['mmd'], // deliberately NOT the old hardcoded default
      });

      expect(ArtifactDownloader.formatsFor(artifact), [DownloadFormat.mmd]);
    });

    test('an unrecognised downloads entry is skipped rather than crashing',
        () {
      final artifact = ChatArtifact.fromJson(const {
        'kind': 'markdown',
        'source': 'body',
        'downloads': ['pdf', 'zip', 'md'],
      });

      expect(ArtifactDownloader.formatsFor(artifact),
          [DownloadFormat.pdf, DownloadFormat.markdown]);
    });

    test('an artifact with no downloads field offers nothing', () {
      final artifact = ChatArtifact.fromJson(const {
        'kind': 'mermaid',
        'source': 'graph TD; A-->B',
      });

      expect(ArtifactDownloader.formatsFor(artifact), isEmpty);
    });
  });

  group('filename + MIME selection', () {
    test('derives a slug base name from the title', () {
      final a = _diagram(title: 'Auth Flow Diagram!');
      expect(ArtifactDownloader.baseName(a), 'auth-flow-diagram');
      expect(ArtifactDownloader.spec(a, DownloadFormat.svg),
          const DownloadSpec('auth-flow-diagram.svg', 'image/svg+xml'));
      expect(ArtifactDownloader.spec(a, DownloadFormat.png),
          const DownloadSpec('auth-flow-diagram.png', 'image/png'));
      expect(ArtifactDownloader.spec(a, DownloadFormat.pdf),
          const DownloadSpec('auth-flow-diagram.pdf', 'application/pdf'));
      expect(ArtifactDownloader.spec(a, DownloadFormat.mmd),
          const DownloadSpec('auth-flow-diagram.mmd', 'text/plain'));
    });

    test('falls back to a kind default base name when untitled', () {
      expect(ArtifactDownloader.baseName(_diagram()), 'diagram');
      expect(ArtifactDownloader.baseName(_review()), 'code-review');
      expect(ArtifactDownloader.spec(_review(), DownloadFormat.markdown),
          const DownloadSpec('code-review.md', 'text/markdown'));
      expect(ArtifactDownloader.spec(_review(), DownloadFormat.pdf),
          const DownloadSpec('code-review.pdf', 'application/pdf'));
    });
  });

  group('labels', () {
    test('label() has a human-readable string for every format', () {
      expect(ArtifactDownloader.label(DownloadFormat.svg), 'SVG');
      expect(ArtifactDownloader.label(DownloadFormat.png), 'PNG');
      expect(ArtifactDownloader.label(DownloadFormat.pdf), 'PDF');
      expect(ArtifactDownloader.label(DownloadFormat.markdown), 'Markdown');
      expect(ArtifactDownloader.label(DownloadFormat.mmd), 'Mermaid source');
    });
  });

  group('byte builders', () {
    test('svgBytes returns the exact SVG bytes', () {
      final a = _diagram(svg: '<svg id="x"></svg>');
      expect(ArtifactDownloader.svgBytes(a),
          utf8.encode('<svg id="x"></svg>'));
    });

    test('svgBytes throws when there is no SVG', () {
      expect(() => ArtifactDownloader.svgBytes(_diagram()),
          throwsA(isA<StateError>()));
    });

    test('markdownBytes returns the exact markdown bytes', () {
      final a = _review();
      expect(ArtifactDownloader.markdownBytes(a), utf8.encode(a.markdown!));
    });

    test('sourceBytes returns the exact Mermaid source bytes', () {
      final a = _diagram();
      expect(ArtifactDownloader.sourceBytes(a), utf8.encode(a.source!));
    });

    test('sourceBytes throws when there is no source', () {
      const noSource = ChatArtifact(kind: ArtifactKind.mermaid);
      expect(() => ArtifactDownloader.sourceBytes(noSource),
          throwsA(isA<StateError>()));
    });

    test('codeReviewPdf builds a valid PDF document', () async {
      final bytes = await ArtifactDownloader.codeReviewPdf(_review());
      expect(_isPdf(bytes), isTrue);
      expect(bytes.length, greaterThan(400));
    });

    // REGRESSION PIN (H5, PDF path): the exported PDF used the same
    // table-less Markdown renderer, so a code-review Findings table landed as
    // literal `|---|`/`| ERROR |` lines. The renderer must now consume the
    // pipe-table without throwing and still emit a valid PDF.
    test('codeReviewPdf renders a Markdown pipe-table without error', () async {
      final withTable = ChatArtifact.fromJson(const {
        'kind': 'markdown',
        'source': '## Findings\n\n'
            '| Severity | Finding | Location |\n'
            '|----------|---------|----------|\n'
            '| ERROR | SQL injection | db.py:42 |\n'
            '| WARN | Missing retry | api.py:10 |\n',
        'downloads': ['pdf', 'md'],
      });
      final bytes = await ArtifactDownloader.codeReviewPdf(withTable);
      expect(_isPdf(bytes), isTrue);
      expect(bytes.length, greaterThan(400));
    });

    // REGRESSION PIN (PDF path): a prose line containing a `|` followed by a
    // bare `---` rule must NOT be mis-parsed as a table in the export either.
    // Shared with the live view via lib/util/markdown_table.dart, so this
    // guards the PDF renderer against silently swallowing the following prose.
    test('codeReviewPdf does not mis-parse a prose "|" + "---" as a table',
        () async {
      final artifact = ChatArtifact.fromJson(const {
        'kind': 'markdown',
        'source': '## Notes\n\n'
            'Use the pipe | operator to combine streams.\n'
            '---\n'
            'That rule above is a divider, not a table.\n',
        'downloads': ['pdf', 'md'],
      });
      final bytes = await ArtifactDownloader.codeReviewPdf(artifact);
      expect(_isPdf(bytes), isTrue);
      expect(bytes.length, greaterThan(400));
    });

    test('diagramPdf embeds the SVG into a valid PDF', () async {
      final bytes = await ArtifactDownloader.diagramPdf(
        _diagram(svg: '<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'),
      );
      expect(_isPdf(bytes), isTrue);
    });

    test('diagramPdf typesets the source when no SVG is present', () async {
      final bytes = await ArtifactDownloader.diagramPdf(_diagram());
      expect(_isPdf(bytes), isTrue);
    });
  });

  group('bytesFor dispatch', () {
    const downloader = ArtifactDownloader();

    test('pdf for a diagram produces a diagram PDF', () async {
      final bytes = await downloader.bytesFor(
          _diagram(svg: '<svg></svg>'), DownloadFormat.pdf);
      expect(_isPdf(bytes), isTrue);
    });

    test('pdf for a code-review produces a review PDF', () async {
      final bytes =
          await downloader.bytesFor(_review(), DownloadFormat.pdf);
      expect(_isPdf(bytes), isTrue);
    });

    test('markdown dispatch returns markdown bytes', () async {
      final a = _review();
      final bytes = await downloader.bytesFor(a, DownloadFormat.markdown);
      expect(bytes, utf8.encode(a.markdown!));
    });

    test('mmd dispatch returns the raw source bytes', () async {
      final a = _diagram();
      final bytes = await downloader.bytesFor(a, DownloadFormat.mmd);
      expect(bytes, utf8.encode(a.source!));
    });
  });
}
