import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_ai_chat/models/chat_stream_event.dart';
import 'package:flutter_ai_chat/models/citation.dart';
import 'package:flutter_ai_chat/models/conversation_turn.dart';
import 'package:flutter_ai_chat/models/chat_skill.dart';
import 'package:flutter_ai_chat/models/system_status.dart';
import 'package:flutter_ai_chat/services/ai_backend.dart';
import 'package:flutter_ai_chat/services/backend_exception.dart';
import 'package:flutter_ai_chat/state/chat_controller.dart';
import 'package:flutter_ai_chat/state/status_controller.dart';
import 'package:flutter_ai_chat/ui/chat_screen.dart';
import 'package:flutter_ai_chat/ui/widgets/skill_selector.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

/// A fully in-memory fake backend. The widget tests drive the real UI and
/// state through the streamed `/chat` contract, but never hit the network.
class FakeBackend implements AiBackend {
  FakeBackend({this.failAuth = false, this.script});

  final bool failAuth;

  /// Optional override of the streamed events. When null, a default grounded
  /// answer (metadata + tokens + done) is streamed.
  final List<ChatStreamEvent>? script;

  bool asked = false;
  int chatCalls = 0;
  String? lastMessage;
  List<ConversationTurn>? lastHistory;
  String? lastSessionId;
  String? lastSkill;

  static const _defaultCitation = Citation(
    documentId: 2,
    documentTitle: 'Stateless services scale horizontally',
    chunkId: 5,
    text: 'Any instance can handle any request.',
    score: 0.7,
  );

  @override
  Future<void> authenticate() async {
    if (failAuth) {
      throw const BackendException('demo sign-in failed', isAuth: true);
    }
  }

  @override
  Stream<ChatStreamEvent> chat({
    required String message,
    required List<ConversationTurn> history,
    int? topK,
    String? sessionId,
    String? skill,
  }) async* {
    asked = true;
    chatCalls++;
    lastMessage = message;
    lastHistory = history;
    lastSessionId = sessionId;
    lastSkill = skill;

    final events = script ??
        const <ChatStreamEvent>[
          ChatMetadata(
            model: 'fake',
            retrieved: 1,
            citations: [_defaultCitation],
          ),
          ChatToken('Stateless instances '),
          ChatToken('sit behind a load balancer.'),
          ChatDone('stop'),
        ];

    for (final event in events) {
      yield event;
    }
  }
}

/// A backend whose single `/chat` stream is driven by the test, so a test can
/// observe a transient in-flight state (queue wait, mid-stream truncation)
/// before the turn resolves, and control exactly when tokens land relative to
/// user scrolling.
class ControllableBackend implements AiBackend {
  final StreamController<ChatStreamEvent> _events =
      StreamController<ChatStreamEvent>();

  void emit(ChatStreamEvent event) => _events.add(event);
  Future<void> finish() => _events.close();

  @override
  Future<void> authenticate() async {}

  @override
  Stream<ChatStreamEvent> chat({
    required String message,
    required List<ConversationTurn> history,
    int? topK,
    String? sessionId,
    String? skill,
  }) =>
      _events.stream;
}

/// A status controller for the functional tests. It is seeded to the neutral
/// "unavailable" state and never started, so the banner dot does not pulse
/// (a perpetual animation would block `pumpAndSettle`). These tests assert chat
/// behaviour, not the banner, which has its own suite in status_banner_test.dart.
StatusController _idleStatus() => StatusController(
      fetcher: () async =>
          const SystemStatus(tier: '', gpuOnline: false, model: ''),
    );

Widget _wrap(AiBackend backend) {
  return MultiProvider(
    providers: [
      ChangeNotifierProvider(create: (_) => ChatController(backend)..connect()),
      ChangeNotifierProvider<StatusController>(create: (_) => _idleStatus()),
    ],
    child: MaterialApp(home: const ChatScreen()),
  );
}

/// Pump the app at a realistic desktop-web viewport, the app's primary target.
Future<void> _pump(WidgetTester tester, AiBackend backend) async {
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

void main() {
  testWidgets('shows the branded empty state on a ready session',
      (tester) async {
    await _pump(tester, FakeBackend());

    expect(find.text('AI-First Assistant'), findsOneWidget);
    expect(
      find.text('Ask me anything, grounded in real sources'),
      findsOneWidget,
    );
    expect(find.text('Connected'), findsOneWidget);
  });

  testWidgets('streams an answer and renders it with its citation',
      (tester) async {
    final backend = FakeBackend();
    await _pump(tester, backend);

    await _send(tester, 'how do services scale?');

    expect(backend.asked, isTrue);
    expect(find.text('how do services scale?'), findsOneWidget);
    // The concatenated streamed tokens render as the final answer.
    expect(
      find.text('Stateless instances sit behind a load balancer.'),
      findsOneWidget,
    );
    // The citation (from the leading metadata event) renders.
    expect(find.text('SOURCES'), findsOneWidget);
    expect(
      find.text('Stateless services scale horizontally'),
      findsOneWidget,
    );
  });

  testWidgets('carries prior turns as history on a follow-up question',
      (tester) async {
    final backend = FakeBackend();
    await _pump(tester, backend);

    await _send(tester, 'how do services scale?');
    await _send(tester, 'and how do I avoid duplicate work?');

    // The second request must include the first user+assistant exchange so the
    // backend can answer the follow-up in context.
    expect(backend.lastMessage, 'and how do I avoid duplicate work?');
    final history = backend.lastHistory!;
    expect(history, hasLength(2));
    expect(history[0].role, 'user');
    expect(history[0].content, 'how do services scale?');
    expect(history[1].role, 'assistant');
    expect(history[1].content,
        'Stateless instances sit behind a load balancer.');
  });

  testWidgets(
      'New chat button clears the transcript and rotates the session id',
      (tester) async {
    final backend = FakeBackend();
    await _pump(tester, backend);

    await _send(tester, 'how do services scale?');
    expect(find.text('how do services scale?'), findsOneWidget);
    final firstSessionId = backend.lastSessionId;
    expect(firstSessionId, isNotNull);

    await tester.tap(find.text('New chat'));
    await tester.pumpAndSettle();

    // A conversation was in progress, so a confirmation dialog appears
    // rather than clearing silently.
    expect(find.text('Start a new chat?'), findsOneWidget);
    await tester.tap(
      find.descendant(
        of: find.byType(AlertDialog),
        matching: find.text('New chat'),
      ),
    );
    await tester.pumpAndSettle();

    // The transcript is genuinely cleared: back to the branded empty state.
    expect(find.text('how do services scale?'), findsNothing);
    expect(
      find.text('Ask me anything, grounded in real sources'),
      findsOneWidget,
    );

    // The NEXT message proves the reset is real, not cosmetic: it carries an
    // empty history (so the model gets no memory of the prior exchange) and
    // a brand new session id (so the backend's own audit/learning log sees a
    // clean boundary too).
    await _send(tester, 'and now?');
    expect(backend.lastHistory, isEmpty);
    expect(backend.lastSessionId, isNot(equals(firstSessionId)));
  });

  testWidgets(
      'New chat button clears immediately with no confirmation when the '
      'transcript is already empty', (tester) async {
    final backend = FakeBackend();
    await _pump(tester, backend);

    await tester.tap(find.text('New chat'));
    await tester.pumpAndSettle();

    expect(find.text('Start a new chat?'), findsNothing);
    expect(
      find.text('Ask me anything, grounded in real sources'),
      findsOneWidget,
    );
  });

  testWidgets('shows the offline banner when the demo session fails',
      (tester) async {
    await _pump(tester, FakeBackend(failAuth: true));

    expect(find.text('Offline'), findsOneWidget);
    expect(find.text('demo sign-in failed'), findsOneWidget);
    expect(find.text('Reconnect'), findsOneWidget);
  });

  testWidgets('renders a polite ungrounded state when no citations stream',
      (tester) async {
    final backend = FakeBackend(
      script: const [
        ChatMetadata(model: 'fake', retrieved: 0, citations: []),
        ChatToken('I can only answer in general terms here.'),
        ChatDone('stop'),
      ],
    );
    await _pump(tester, backend);

    await _send(tester, 'something obscure');

    expect(find.text('No grounded source'), findsOneWidget);
    expect(find.text('SOURCES'), findsNothing);
  });

  testWidgets('surfaces a streamed error event as an error turn',
      (tester) async {
    final backend = FakeBackend(
      script: const [
        ChatMetadata(model: 'fake', retrieved: 0, citations: []),
        ChatStreamError(message: 'The local LLM is unreachable.', type: 'x'),
        ChatDone('error'),
      ],
    );
    await _pump(tester, backend);

    await _send(tester, 'anything');

    expect(find.text('The local LLM is unreachable.'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  group('skill selector', () {
    testWidgets(
        'is visible on the empty/welcome screen with "Ask a question" '
        'selected by default', (tester) async {
      await _pump(tester, FakeBackend());

      expect(find.byKey(kSkillSelectorKey), findsOneWidget);
      expect(find.text('Ask a question'), findsOneWidget);
      expect(find.text('Review my code'), findsOneWidget);
      expect(find.text('Generate a diagram'), findsOneWidget);
    });

    testWidgets('defaults to sending the qa skill with no explicit tap',
        (tester) async {
      final backend = FakeBackend();
      await _pump(tester, backend);

      await _send(tester, 'how do services scale?');

      expect(backend.lastSkill, 'qa');
    });

    testWidgets(
        'tapping "Review my code" sends skill=code-review and updates the '
        'composer hint', (tester) async {
      final backend = FakeBackend();
      await _pump(tester, backend);

      await tester.tap(find.text('Review my code'));
      await tester.pumpAndSettle();

      expect(
        find.text('Paste code, a Dockerfile or CI config to review...'),
        findsOneWidget,
      );

      await _send(tester, 'def foo(): pass');
      expect(backend.lastSkill, 'code-review');
    });

    testWidgets(
        'tapping "Generate a diagram" sends skill=mermaid and updates the '
        'composer hint', (tester) async {
      final backend = FakeBackend();
      await _pump(tester, backend);

      await tester.tap(find.text('Generate a diagram'));
      await tester.pumpAndSettle();

      expect(
        find.text('Describe what you want diagrammed...'),
        findsOneWidget,
      );

      await _send(tester, 'the request lifecycle');
      expect(backend.lastSkill, 'mermaid');
    });

    testWidgets('stays visible and selectable once a conversation is active',
        (tester) async {
      final backend = FakeBackend();
      await _pump(tester, backend);

      await _send(tester, 'how do services scale?');

      // The transcript is now showing (not the empty state), but the
      // selector must still be present and usable.
      expect(find.byKey(kSkillSelectorKey), findsOneWidget);
      await tester.tap(find.text('Review my code'));
      await tester.pumpAndSettle();

      await _send(tester, 'def bar(): pass');
      expect(backend.lastSkill, 'code-review');
    });

    // REGRESSION PIN (FE L6): when the selector is disabled (e.g. while the
    // client is connecting or a send is in flight) the chips were still drawn
    // at full opacity, giving no visual cue that they are not tappable - the
    // `onTap` was gated but the UI looked live. The chips must dim.
    Future<Iterable<double>> chipOpacities(
      WidgetTester tester, {
      required bool enabled,
    }) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SkillSelector(
              selected: ChatSkill.qa,
              enabled: enabled,
              onChanged: (_) {},
            ),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 200));
      final row = find.byKey(kSkillSelectorKey);
      return tester
          .widgetList<AnimatedOpacity>(
            find.descendant(of: row, matching: find.byType(AnimatedOpacity)),
          )
          .map((w) => w.opacity);
    }

    testWidgets('chips render at full opacity when enabled', (tester) async {
      final opacities = await chipOpacities(tester, enabled: true);
      expect(opacities, isNotEmpty);
      expect(opacities.every((o) => o == 1.0), isTrue);
    });

    testWidgets('chips dim to signal they are not tappable when disabled',
        (tester) async {
      final opacities = await chipOpacities(tester, enabled: false);
      expect(opacities, isNotEmpty);
      expect(opacities.every((o) => o == kDisabledSkillChipOpacity), isTrue);
      expect(kDisabledSkillChipOpacity, lessThan(1.0));
    });
  });

  group('honest non-answer states (not the "no grounded answer" catch-all)', () {
    testWidgets(
        'a busy stream renders the at-capacity state with a retry, never the '
        'no-grounded-answer copy', (tester) async {
      final backend = FakeBackend(
        script: const [
          ChatBusy(
            message: 'The demo is at capacity right now. Please try again '
                'in a few seconds.',
          ),
          ChatDone('busy'),
        ],
      );
      await _pump(tester, backend);

      await _send(tester, 'anything');

      expect(find.textContaining('at capacity'), findsOneWidget);
      expect(
        find.textContaining('could not find a grounded answer'),
        findsNothing,
      );
      expect(find.text('Retry'), findsOneWidget);

      // Regression pin: Retry on the at-capacity bubble must actually resend.
      // retryLast() previously gated on `status == error` only, so tapping
      // Retry on a busy bubble was a dead control - no second backend call.
      expect(backend.chatCalls, 1);
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(backend.chatCalls, 2, reason: 'Retry on busy must resend');
    });

    testWidgets(
        'an offline stream renders the paused-demo notice, never the '
        'no-grounded-answer copy, and Retry resends', (tester) async {
      final backend = FakeBackend(
        script: const [
          ChatMetadata(model: 'offline', retrieved: 0, citations: []),
          ChatNotice(
            message: 'The live demo is paused right now (the GPU is training).',
          ),
          ChatDone('offline'),
        ],
      );
      await _pump(tester, backend);

      await _send(tester, 'anything');

      expect(find.textContaining('paused'), findsOneWidget);
      expect(
        find.textContaining('could not find a grounded answer'),
        findsNothing,
      );

      // Regression pin: Retry on the offline bubble must actually resend, too.
      expect(find.text('Retry'), findsOneWidget);
      expect(backend.chatCalls, 1);
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(backend.chatCalls, 2, reason: 'Retry on offline must resend');
    });

    testWidgets(
        'a mid-stream offline keeps the partial answer and flags the '
        'truncation instead of marking it complete', (tester) async {
      final backend = FakeBackend(
        script: const [
          ChatMetadata(model: 'm', retrieved: 0, citations: []),
          ChatToken('Stateless services sit behind '),
          ChatNotice(message: 'The live demo is paused right now.'),
          ChatDone('offline'),
        ],
      );
      await _pump(tester, backend);

      await _send(tester, 'how do services scale?');

      // The partial answer survives...
      expect(find.textContaining('Stateless services sit behind'), findsOneWidget);
      // ...and is honestly flagged as cut off, not silently "finished".
      expect(find.textContaining('cut off'), findsOneWidget);
      expect(find.textContaining('paused'), findsOneWidget);
    });

    testWidgets('a queued turn shows honest waiting-in-line position feedback',
        (tester) async {
      final backend = ControllableBackend();
      tester.view.physicalSize = const Size(1280, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(_wrap(backend));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'q under load');
      await tester.pump();
      await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
      await tester.pump();

      backend.emit(const ChatQueue(position: 3, status: 'waiting'));
      await tester.pump();

      // A distinct "position 3" waiting state, not a bare frozen spinner.
      expect(find.textContaining('position 3'), findsOneWidget);

      // The turn then resolves normally once a slot frees.
      backend.emit(const ChatMetadata(model: 'm', retrieved: 0, citations: []));
      backend.emit(const ChatToken('Answer text.'));
      backend.emit(const ChatDone('stop'));
      await backend.finish();
      await tester.pumpAndSettle();

      expect(find.textContaining('position 3'), findsNothing);
      expect(find.textContaining('Answer text.'), findsOneWidget);
    });
  });

  group('composer guards', () {
    testWidgets('enforces the backend message length cap with a visible counter',
        (tester) async {
      await _pump(tester, FakeBackend());

      await tester.enterText(find.byType(TextField), 'x' * 5000);
      await tester.pump();

      final field = tester.widget<TextField>(find.byType(TextField));
      expect(field.maxLength, 4000);
      expect(find.textContaining('Message limit reached'), findsOneWidget);
    });

    testWidgets('numpad Enter submits the message (L7)', (tester) async {
      final backend = FakeBackend();
      await _pump(tester, backend);

      await tester.enterText(find.byType(TextField), 'sent via numpad');
      await tester.pump();
      await tester.sendKeyEvent(LogicalKeyboardKey.numpadEnter);
      await tester.pumpAndSettle();

      expect(backend.lastMessage, 'sent via numpad');
    });

    testWidgets(
        'suggestion chips honour the composer gate: a tap while the session '
        'is not ready does not fire a send (M6)', (tester) async {
      // A failed session keeps the empty state (with its chips) on screen but
      // with the gate closed - a deterministic stand-in for any not-ready
      // state. Tapping a chip must not slip a request past the gate.
      final backend = FakeBackend(failAuth: true);
      await _pump(tester, backend);

      expect(find.text('Offline'), findsOneWidget); // session not ready
      expect(find.text('How do stateless services scale?'), findsOneWidget);

      await tester.tap(find.text('How do stateless services scale?'));
      await tester.pump();

      expect(backend.asked, isFalse);
    });
  });

  group('transcript behaviour', () {
    testWidgets('only the most recent error bubble offers Retry (L2)',
        (tester) async {
      final backend = FakeBackend(
        script: const [
          ChatStreamError(message: 'The local LLM is unreachable.', type: 'x'),
          ChatDone('error'),
        ],
      );
      await _pump(tester, backend);

      await _send(tester, 'first');
      await _send(tester, 'second');

      // Two error bubbles are shown...
      expect(find.text('The local LLM is unreachable.'), findsNWidgets(2));
      // ...but only the last one carries the Retry affordance, which is the
      // only one retryLast() would actually act on.
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets(
        'a streaming answer does not yank the view down when the user has '
        'scrolled up to read earlier messages (M3)', (tester) async {
      final backend = ControllableBackend();
      tester.view.physicalSize = const Size(1280, 700);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(_wrap(backend));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'q');
      await tester.pump();
      await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
      await tester.pump();

      backend.emit(const ChatMetadata(model: 'm', retrieved: 0, citations: []));
      // Stream a long answer so the transcript overflows and can be scrolled.
      // NOTE: do NOT pumpAndSettle while streaming - the blinking caret
      // animates forever and would time it out; advance with fixed pumps so
      // the paced reveal reaches full height instead.
      final answer =
          List.generate(60, (i) => 'Paragraph line number $i. ').join('\n');
      backend.emit(ChatToken(answer));
      await tester.pump();
      await tester.pump(const Duration(seconds: 2));

      // The transcript ListView's own Scrollable (the SelectableText answers
      // each nest their own inner Scrollable, so take the outermost/first).
      final scrollableFinder = find
          .descendant(
            of: find.byType(ListView),
            matching: find.byType(Scrollable),
          )
          .first;
      final position =
          tester.state<ScrollableState>(scrollableFinder).position;

      // User scrolls up to read earlier content.
      await tester.drag(scrollableFinder, const Offset(0, 400));
      await tester.pump();
      final offsetAfterScrollUp = position.pixels;
      expect(offsetAfterScrollUp, lessThan(position.maxScrollExtent));

      // More tokens arrive while the user is reading up-thread.
      backend.emit(const ChatToken('\nMore streamed text arriving now.'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // The view was NOT hijacked back to the bottom.
      expect(position.pixels, lessThan(position.maxScrollExtent - 10));

      // Finish the turn so nothing keeps animating, then let it settle.
      backend.emit(const ChatDone('stop'));
      await backend.finish();
      await tester.pump();
      await tester.pump(const Duration(seconds: 2));
    });
  });
}
