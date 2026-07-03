import 'package:flutter/material.dart';
import 'package:flutter_ai_chat/models/chat_artifact.dart';
import 'package:flutter_ai_chat/models/chat_message.dart';
import 'package:flutter_ai_chat/models/chat_stream_event.dart';
import 'package:flutter_ai_chat/models/conversation_turn.dart';
import 'package:flutter_ai_chat/services/ai_backend.dart';
import 'package:flutter_ai_chat/services/artifact_download.dart';
import 'package:flutter_ai_chat/state/chat_controller.dart';
import 'package:flutter_ai_chat/ui/widgets/artifact_view.dart';
import 'package:flutter_test/flutter_test.dart';

// Widget-level coverage for the inline artifact card + download menu (rendered
// on the VM, where Mermaid degrades to a source code block), and a controller
// test that a streamed artifact event is attached to the assistant message.

ChatArtifact _diagram() => const ChatArtifact(
      kind: ArtifactKind.mermaid,
      title: 'Auth flow',
      source: 'graph TD; Client-->API; API-->DB',
      // A pre-rendered SVG is present, so svg/png downloads are producible and
      // therefore offered (see the M5 filter in ArtifactDownloader.formatsFor).
      svg: '<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>',
      downloads: ['pdf', 'svg', 'png', 'mmd'],
    );

ChatArtifact _review() => const ChatArtifact(
      kind: ArtifactKind.markdown,
      title: 'Review',
      markdown: '# Findings\n- Worker is not idempotent',
      downloads: ['pdf', 'md'],
    );

Future<void> _pump(WidgetTester tester, ChatArtifact artifact) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(child: ArtifactView(artifact: artifact)),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

class _ArtifactBackend implements AiBackend {
  _ArtifactBackend(this.artifact);
  final ChatArtifact artifact;

  @override
  Future<void> authenticate() async {}

  @override
  Stream<ChatStreamEvent> chat({
    required String message,
    required List<ConversationTurn> history,
    int? topK,
    String? sessionId,
    String? skill,
  }) async* {
    yield const ChatMetadata(model: 'fake', retrieved: 0, citations: []);
    yield ChatArtifactEvent(artifact);
    yield const ChatToken('Here is the diagram.');
    yield const ChatDone('stop');
  }
}

void main() {
  testWidgets('diagram artifact shows the source fallback + diagram downloads',
      (tester) async {
    await _pump(tester, _diagram());

    // The Mermaid source degrades to a code block on the VM.
    expect(find.textContaining('graph TD'), findsOneWidget);
    expect(find.text('Auth flow'), findsOneWidget);

    // Open the download menu and assert the three diagram formats.
    await tester.tap(find.byType(PopupMenuButton<DownloadFormat>));
    await tester.pumpAndSettle();
    expect(find.text('SVG'), findsOneWidget);
    expect(find.text('PNG'), findsOneWidget);
    expect(find.text('PDF'), findsOneWidget);
  });

  testWidgets('code-review artifact renders markdown + PDF/Markdown downloads',
      (tester) async {
    await _pump(tester, _review());

    expect(find.text('Findings'), findsOneWidget);

    await tester.tap(find.byType(PopupMenuButton<DownloadFormat>));
    await tester.pumpAndSettle();
    expect(find.text('PDF'), findsOneWidget);
    expect(find.text('Markdown'), findsOneWidget);
    expect(find.text('SVG'), findsNothing);
  });

  // REGRESSION PIN: a REAL backend `event: artifact` payload never carries a
  // `markdown` key - every kind's body lives in `source` (see
  // `fastapi-ai-devtools-demo/app/routers/chat.py`'s artifact yield). This
  // test builds the artifact via `ChatArtifact.fromJson` from that exact wire
  // shape (not by hand-constructing a `ChatArtifact` with `markdown:` set
  // directly, which is what the test above does and which cannot catch this
  // bug). Before the fix, `_MarkdownBody` only read `artifact.markdown`
  // (always null for a real payload), so the card rendered completely empty
  // even though the full review text was sitting right there in `source` -
  // this is the concrete "code review is not available easily" symptom.
  testWidgets(
      'a real-shape code-review artifact (no markdown key on the wire) '
      'still shows the review text instead of an empty card', (tester) async {
    final artifact = ChatArtifact.fromJson(const {
      'kind': 'markdown',
      'format': 'markdown',
      'source': '## Findings\n- Worker is not idempotent',
      'svg': null,
      'downloads': ['pdf', 'md'],
    });

    await _pump(tester, artifact);

    expect(find.textContaining('Worker is not idempotent'), findsOneWidget);
  });

  // REGRESSION PIN: same real wire shape as above, but for the mermaid skill.
  // Before the fix, `ChatArtifact.fromJson` read `json['type']` (never sent
  // by the backend, which sends `kind`), so `artifact.kind` always decoded as
  // `ArtifactKind.unknown` and `isDiagram` was always false - a real Mermaid
  // artifact never reached `MermaidView` at all, it fell into the (empty)
  // markdown branch above. This asserts the diagram branch is actually taken
  // (the VM-test fallback renders the Mermaid source as a code block, proving
  // `MermaidView` - not `_MarkdownBody` - handled it).
  testWidgets(
      'a real-shape mermaid artifact (kind on the wire, no pre-rendered svg) '
      'is routed to MermaidView, not the empty markdown branch', (tester) async {
    final artifact = ChatArtifact.fromJson(const {
      'kind': 'mermaid',
      'format': 'mermaid',
      'source': 'graph TD; A-->B',
      'svg': null,
      'downloads': ['pdf', 'svg', 'png', 'mmd'],
    });

    expect(artifact.isDiagram, isTrue);
    await _pump(tester, artifact);

    // MermaidView's VM/test fallback shows the Mermaid source as a code
    // block; _MarkdownBody would show nothing since `markdown` is null.
    expect(find.textContaining('graph TD'), findsOneWidget);
  });

  // REGRESSION PIN: the download menu used to be built from a second,
  // hand-maintained list keyed off `artifact.isDiagram` (always
  // [svg, png, pdf] for any diagram) instead of the backend's actual
  // `downloads` field - a silent drift risk since nothing tested it. This
  // artifact IS a diagram (`kind: mermaid`, `isDiagram == true`) but its
  // `downloads` deliberately omits svg/png and includes the `.mmd` format
  // the old hardcoded list never offered at all. Under the old logic this
  // would still show SVG + PNG and no "Mermaid source" option; after the fix
  // the menu shows exactly what `downloads` says, no more, no less.
  testWidgets(
      'download menu reflects the downloads field exactly, not a hardcoded '
      'per-kind list', (tester) async {
    final artifact = ChatArtifact.fromJson(const {
      'kind': 'mermaid',
      'source': 'graph TD; A-->B',
      'downloads': ['pdf', 'mmd'],
    });

    await _pump(tester, artifact);

    await tester.tap(find.byType(PopupMenuButton<DownloadFormat>));
    await tester.pumpAndSettle();

    expect(find.text('PDF'), findsOneWidget);
    expect(find.text('Mermaid source'), findsOneWidget);
    expect(find.text('SVG'), findsNothing);
    expect(find.text('PNG'), findsNothing);
  });

  // REGRESSION PIN (M5): in prod the mermaid skill runs with server-side SVG
  // rendering OFF, so a real diagram has `svg == null` yet its `downloads`
  // still advertises svg/png. The menu used to offer them anyway; picking
  // either threw and then showed a misleading "available on the web build"
  // snackbar. The menu must now hide svg/png when no SVG is present.
  testWidgets(
      'download menu hides SVG/PNG for a diagram with no pre-rendered SVG',
      (tester) async {
    final artifact = ChatArtifact.fromJson(const {
      'kind': 'mermaid',
      'source': 'graph TD; A-->B',
      'svg': null,
      'downloads': ['pdf', 'svg', 'png', 'mmd'],
    });

    await _pump(tester, artifact);
    await tester.tap(find.byType(PopupMenuButton<DownloadFormat>));
    await tester.pumpAndSettle();

    expect(find.text('PDF'), findsOneWidget);
    expect(find.text('Mermaid source'), findsOneWidget);
    expect(find.text('SVG'), findsNothing);
    expect(find.text('PNG'), findsNothing);
  });

  // REGRESSION PIN (H5): the code-review skill's Findings output is a mandated
  // Markdown pipe-table. The lightweight `_MarkdownBody` had no table support,
  // so the `| Severity | ... |` header, the `|---|` separator and every data
  // row rendered as literal pipe text - the flagship code-review card looked
  // broken. It must now render the cell values as a real table (and never show
  // the raw separator row).
  testWidgets('a Markdown pipe-table renders as a table, not raw pipe rows',
      (tester) async {
    final artifact = ChatArtifact.fromJson(const {
      'kind': 'markdown',
      'source': '## Findings\n\n'
          '| Severity | Finding | Location |\n'
          '|----------|---------|----------|\n'
          '| ERROR | SQL injection | db.py:42 |\n'
          '| WARN | Missing retry | api.py:10 |\n',
      'downloads': ['pdf', 'md'],
    });

    await _pump(tester, artifact);

    expect(find.byType(Table), findsOneWidget);
    expect(find.text('Severity'), findsOneWidget);
    expect(find.text('SQL injection'), findsOneWidget);
    expect(find.text('db.py:42'), findsOneWidget);
    // The raw pipe/separator markup must not survive to the screen.
    expect(find.textContaining('|---'), findsNothing);
    expect(find.textContaining('| Severity |'), findsNothing);
  });

  // REGRESSION PIN: a prose line that merely contains a `|` followed by a bare
  // `---` horizontal rule was mis-parsed as a one-column table, which SWALLOWED
  // the surrounding text. The separator now requires a pipe AND a column count
  // matching the header (GFM), so this is plain text and nothing is a Table.
  testWidgets('a prose "|" line before a "---" rule is not a false table',
      (tester) async {
    final artifact = ChatArtifact.fromJson(const {
      'kind': 'markdown',
      'source': '## Notes\n\n'
          'Use the pipe | operator to combine streams.\n'
          '---\n'
          'That rule above is a divider, not a table.\n',
      'downloads': ['pdf', 'md'],
    });

    await _pump(tester, artifact);

    // No table should be built from a divider...
    expect(find.byType(Table), findsNothing);
    // ...and the prose that used to be swallowed must survive.
    expect(
      find.textContaining('Use the pipe | operator to combine streams.'),
      findsOneWidget,
    );
    expect(
      find.textContaining('That rule above is a divider'),
      findsOneWidget,
    );
  });

  testWidgets('a streamed artifact event is attached to the message',
      (tester) async {
    final controller = ChatController(_ArtifactBackend(_diagram()));
    addTearDown(controller.dispose);
    await controller.connect();

    await controller.send('show me the auth flow');

    final last = controller.messages.last;
    expect(last.artifacts, hasLength(1));
    expect(last.artifacts.first.kind, ArtifactKind.mermaid);
    expect(last.status, MessageStatus.complete);
    // Artifact-bearing answer is not flagged as "ungrounded/empty".
    expect(last.text, 'Here is the diagram.');
  });
}
