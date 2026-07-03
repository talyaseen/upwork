import 'package:flutter/material.dart';
import 'package:flutter_ai_chat/app/theme.dart';
import 'package:flutter_ai_chat/models/chat_message.dart';
import 'package:flutter_ai_chat/models/chat_skill.dart';
import 'package:flutter_ai_chat/models/chat_stream_event.dart';
import 'package:flutter_ai_chat/models/conversation_turn.dart';
import 'package:flutter_ai_chat/models/system_status.dart';
import 'package:flutter_ai_chat/services/ai_backend.dart';
import 'package:flutter_ai_chat/state/chat_controller.dart';
import 'package:flutter_ai_chat/state/status_controller.dart';
import 'package:flutter_ai_chat/ui/chat_screen.dart';
import 'package:flutter_ai_chat/ui/widgets/message_bubble.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

// ACTIVE-SKILL REFLECTION: the backend now AUTO-ROUTES each message to the
// right skill (qa / code-review / mermaid) regardless of the selected mode, and
// reports the skill it actually ran on the metadata event. The UI must reflect
// this so the user is never confused about which skill handled their message:
//   1. each assistant reply carries a badge naming the routed skill, and
//   2. the composer's skill selector syncs to what actually ran (so the
//      dropdown is an honest mirror, not a stale trap that silently mismatches).

/// A fake backend that streams a scripted set of events for every `/chat` call.
class _ScriptedBackend implements AiBackend {
  _ScriptedBackend(this.script);

  final List<ChatStreamEvent> script;
  String? lastSkill;

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
    lastSkill = skill;
    for (final event in script) {
      yield event;
    }
  }
}

StatusController _idleStatus() => StatusController(
      fetcher: () async =>
          const SystemStatus(tier: '', gpuOnline: false, model: ''),
    );

Widget _wrap(AiBackend backend) => MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ChatController(backend)..connect()),
        ChangeNotifierProvider<StatusController>(create: (_) => _idleStatus()),
      ],
      child: MaterialApp(home: const ChatScreen()),
    );

Future<void> _pumpScreen(WidgetTester tester, AiBackend backend) async {
  tester.view.physicalSize = const Size(1280, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(_wrap(backend));
  await tester.pumpAndSettle();
}

Future<void> _send(WidgetTester tester, String text) async {
  await tester.enterText(find.byType(TextField), text);
  await tester.pump();
  await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
  await tester.pumpAndSettle();
}

ChatMessage _assistant(String text, {ChatSkill? routedSkill}) => ChatMessage(
      id: 'a1',
      role: MessageRole.assistant,
      text: text,
      status: MessageStatus.complete,
      routedSkill: routedSkill,
    );

Future<void> _pumpBubble(WidgetTester tester, ChatMessage message) async {
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
  group('ChatSkill.fromId', () {
    test('maps every wire id back to its skill', () {
      expect(ChatSkill.fromId('qa'), ChatSkill.qa);
      expect(ChatSkill.fromId('code-review'), ChatSkill.codeReview);
      expect(ChatSkill.fromId('mermaid'), ChatSkill.mermaid);
    });

    test('returns null for a null, empty or unknown id', () {
      expect(ChatSkill.fromId(null), isNull);
      expect(ChatSkill.fromId(''), isNull);
      expect(ChatSkill.fromId('nonsense'), isNull);
    });
  });

  group('controller reflects the routed skill', () {
    testWidgets(
        'tags the assistant turn with the routed skill and syncs the selector '
        'to what actually ran', (tester) async {
      // The user leaves the default qa mode selected, but the backend routes the
      // turn to code-review and reports that on metadata.
      final backend = _ScriptedBackend(const [
        ChatMetadata(model: 'm', retrieved: 0, citations: [], skill: 'code-review'),
        ChatToken('Reviewed.'),
        ChatDone('stop'),
      ]);
      final controller = ChatController(backend)..connect();
      await tester.pump();

      expect(controller.skill, ChatSkill.qa, reason: 'starts on the default');

      await controller.send('paste of some code');

      // The reply is tagged with the skill that ACTUALLY ran...
      expect(controller.messages.last.routedSkill, ChatSkill.codeReview);
      // ...and the selector is synced to it, so the dropdown mirrors reality
      // instead of silently staying on the stale qa selection. The client still
      // sent its selected hint (qa) as the tiebreaker.
      expect(backend.lastSkill, 'qa');
      expect(controller.skill, ChatSkill.codeReview);
    });

    testWidgets(
        'leaves the selector untouched and the turn untagged when the backend '
        'reports no routed skill', (tester) async {
      final backend = _ScriptedBackend(const [
        ChatMetadata(model: 'm', retrieved: 0, citations: []),
        ChatToken('Answer.'),
        ChatDone('stop'),
      ]);
      final controller = ChatController(backend)..connect();
      await tester.pump();

      await controller.send('q');

      expect(controller.messages.last.routedSkill, isNull);
      expect(controller.skill, ChatSkill.qa);
    });
  });

  group('routed-skill badge', () {
    testWidgets('renders the routed skill label on an assistant reply',
        (tester) async {
      await _pumpBubble(
        tester,
        _assistant('Reviewed your code.', routedSkill: ChatSkill.codeReview),
      );

      expect(find.text('Code review'), findsOneWidget);
      expect(find.byIcon(ChatSkill.codeReview.icon), findsOneWidget);
    });

    testWidgets('shows no badge when the turn carries no routed skill',
        (tester) async {
      await _pumpBubble(tester, _assistant('Plain answer.'));

      expect(find.text('Q&A'), findsNothing);
      expect(find.text('Code review'), findsNothing);
      expect(find.text('Diagram'), findsNothing);
    });

    testWidgets('the badge coexists with the "No grounded source" indicator',
        (tester) async {
      await _pumpBubble(
        tester,
        ChatMessage(
          id: 'a2',
          role: MessageRole.assistant,
          text: 'General answer.',
          status: MessageStatus.complete,
          grounded: false,
          routedSkill: ChatSkill.qa,
        ),
      );

      expect(find.text('Q&A'), findsOneWidget);
      expect(find.text('No grounded source'), findsOneWidget);
    });
  });

  group('end to end on the chat screen', () {
    testWidgets(
        'a message routed to a different skill shows the badge and the selector '
        'reflects the routed skill afterwards', (tester) async {
      // Default qa mode selected; backend auto-routes to mermaid.
      final backend = _ScriptedBackend(const [
        ChatMetadata(model: 'm', retrieved: 0, citations: [], skill: 'mermaid'),
        ChatToken('Here is the diagram.'),
        ChatDone('stop'),
      ]);
      await _pumpScreen(tester, backend);

      await _send(tester, 'show me the request lifecycle');

      // The assistant reply is badged with the skill that actually ran...
      expect(find.text('Diagram'), findsOneWidget);
      // ...and the composer now reflects the routed mode (its placeholder is the
      // mermaid hint), proving the selector synced to reality rather than
      // staying stuck on the qa selection the user started from.
      expect(find.text('Describe what you want diagrammed...'), findsOneWidget);
    });
  });
}
