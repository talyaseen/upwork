import 'package:flutter/material.dart';
import 'package:flutter_ai_chat/app/theme.dart';
import 'package:flutter_ai_chat/models/chat_artifact.dart';
import 'package:flutter_ai_chat/models/chat_message.dart';
import 'package:flutter_ai_chat/ui/widgets/markdown_body.dart';
import 'package:flutter_ai_chat/ui/widgets/message_bubble.dart';
import 'package:flutter_test/flutter_test.dart';

// ISSUE 1 (HIGH): the live assistant message body rendered RAW Markdown -
// `## headings`, GFM pipe-tables and ``` fences showed as literal text, and the
// Mermaid skill dumped its raw ```mermaid source into the prose ABOVE the
// already-rendered diagram card. These widget tests pin the fix: a finished
// assistant body now renders as real Markdown, and the duplicative Mermaid
// fence is suppressed when a diagram artifact is present.

ChatMessage _assistant(
  String text, {
  List<ChatArtifact> artifacts = const [],
}) =>
    ChatMessage(
      id: 'a1',
      role: MessageRole.assistant,
      text: text,
      status: MessageStatus.complete,
      artifacts: artifacts,
    );

Future<void> _pumpBody(WidgetTester tester, ChatMessage message) async {
  tester.view.physicalSize = const Size(1280, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.build(),
      home: Scaffold(
        body: SingleChildScrollView(child: MessageBubble(message: message)),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
      'a findings-table Markdown body renders as a real table, not raw pipe rows',
      (tester) async {
    await _pumpBody(
      tester,
      _assistant(
        '## Findings\n\n'
        '| Severity | Finding | Location |\n'
        '|----------|---------|----------|\n'
        '| ERROR | SQL injection | db.py:42 |\n'
        '| WARN | Missing retry | api.py:10 |\n',
      ),
    );

    expect(find.byType(Table), findsOneWidget);
    expect(find.text('Severity'), findsOneWidget);
    expect(find.text('SQL injection'), findsOneWidget);
    expect(find.text('db.py:42'), findsOneWidget);
    // The raw pipe/separator markup must not survive to the screen.
    expect(find.textContaining('| Severity |'), findsNothing);
    expect(find.textContaining('|---'), findsNothing);
  });

  testWidgets('a "## heading" body renders as a heading, not literal ## text',
      (tester) async {
    await _pumpBody(tester, _assistant('## Overview\n\nSome supporting text.'));

    expect(find.text('Overview'), findsOneWidget);
    expect(find.textContaining('Some supporting text.'), findsOneWidget);
    // The literal heading marker must be gone.
    expect(find.textContaining('## Overview'), findsNothing);
  });

  testWidgets(
      'a ```mermaid fence is suppressed from the body when a diagram artifact '
      'exists (the diagram card already renders it)', (tester) async {
    const diagram = ChatArtifact(
      kind: ArtifactKind.mermaid,
      title: 'Flow',
      source: 'graph TD; A-->B',
    );
    await _pumpBody(
      tester,
      _assistant(
        'Here is your diagram:\n\n'
        '```mermaid\n'
        'graph TD; A-->B\n'
        '```\n\n'
        'Hope it helps.',
        artifacts: [diagram],
      ),
    );

    // Surrounding prose survives...
    expect(find.textContaining('Here is your diagram'), findsOneWidget);
    expect(find.textContaining('Hope it helps'), findsOneWidget);
    // ...the literal fence marker is gone from the body...
    expect(find.textContaining('```mermaid'), findsNothing);
    // ...and the Mermaid source appears exactly ONCE (in the diagram card's
    // VM/test fallback), not duplicated as raw text in the body above it.
    expect(find.textContaining('graph TD; A-->B'), findsOneWidget);
  });

  testWidgets('a plain ```python fence renders as a code block', (tester) async {
    await _pumpBody(
      tester,
      _assistant(
        'Example:\n\n'
        '```python\n'
        'def foo():\n'
        '    return 42\n'
        '```',
      ),
    );

    // The code body renders (as a monospace block)...
    expect(find.textContaining('def foo():'), findsOneWidget);
    // ...with the fence markers stripped, never shown as literal ``` text.
    expect(find.textContaining('```'), findsNothing);
  });

  // Direct unit coverage for the pure strip helper, independent of the widget.
  test('stripMermaidFences removes only the mermaid fence, keeping other code',
      () {
    const input = 'Intro line.\n'
        '```mermaid\n'
        'graph TD; A-->B\n'
        '```\n'
        'Between.\n'
        '```python\n'
        'x = 1\n'
        '```\n'
        'Outro.';
    final out = stripMermaidFences(input);
    expect(out.contains('graph TD'), isFalse);
    expect(out.contains('```mermaid'), isFalse);
    // A non-mermaid fence is left intact.
    expect(out.contains('```python'), isTrue);
    expect(out.contains('x = 1'), isTrue);
    expect(out.contains('Intro line.'), isTrue);
    expect(out.contains('Outro.'), isTrue);
  });
}
