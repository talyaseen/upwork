// Screenshots for portfolio documentation.
//
// Run once to generate or refresh the images in docs/:
//
//   flutter test test/screenshots_test.dart --update-goldens
//
// The generated PNGs are committed to docs/ and embedded in the README.
// On a normal `flutter test` run (without --update-goldens) these tests
// compare against the stored files and pass as long as the UI has not changed.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_ai_chat/models/chat_stream_event.dart';
import 'package:flutter_ai_chat/models/citation.dart';
import 'package:flutter_ai_chat/models/conversation_turn.dart';
import 'package:flutter_ai_chat/models/system_status.dart';
import 'package:flutter_ai_chat/services/ai_backend.dart';
import 'package:flutter_ai_chat/state/chat_controller.dart';
import 'package:flutter_ai_chat/state/status_controller.dart';
import 'package:flutter_ai_chat/ui/chat_screen.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const _viewport = Size(1280, 900);

const _citation1 = Citation(
  documentId: 1,
  documentTitle: 'Stateless services scale horizontally',
  chunkId: 3,
  text: 'Any instance can handle any request because no local state is held '
      'between calls. The load balancer distributes traffic freely across the '
      'pool, and the pool shrinks and grows to match demand.',
  score: 0.91,
);

const _citation2 = Citation(
  documentId: 2,
  documentTitle: 'Twelve-Factor App: Processes',
  chunkId: 7,
  text: 'Twelve-factor processes are stateless and share-nothing. Any data '
      'that needs to persist must be stored in a stateful backing service '
      'such as a database.',
  score: 0.78,
);

// ---------------------------------------------------------------------------
// Fake backends
// ---------------------------------------------------------------------------

/// Standard fake: yields a realistic grounded answer and completes.
class _FakeBackend implements AiBackend {
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
    yield const ChatMetadata(
      model: 'fake',
      retrieved: 2,
      citations: [_citation1, _citation2],
    );
    yield const ChatToken('Stateless instances ');
    yield const ChatToken('sit behind a load balancer ');
    yield const ChatToken('so any node can serve any request. ');
    yield const ChatToken('Scale-out is simply adding more instances ');
    yield const ChatToken('behind the same balancer.');
    yield const ChatDone('stop');
  }
}

/// Paused fake: yields metadata + one token then stalls indefinitely.
/// This keeps the assistant turn in MessageStatus.streaming for a screenshot.
class _PausedFakeBackend implements AiBackend {
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
    yield const ChatMetadata(
      model: 'fake',
      retrieved: 2,
      citations: [_citation1, _citation2],
    );
    yield const ChatToken('Stateless instances sit behind a load balancer');
    // Stall without creating a timer (Future.delayed would leave a pending
    // fake timer that fails Flutter's test invariant check at teardown).
    // A never-resolved Completer creates no timer - it just suspends the
    // async* generator until the stream subscription is cancelled.
    await Completer<void>().future;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Status controller seeded to the GPU-online state so the portfolio
/// screenshots showcase the green "Running on 2x GPUs - ONLINE" banner. It is
/// not started (no polling/network); the dot still pulses, so these tests use
/// bounded pumps rather than pumpAndSettle.
StatusController _onlineStatus() => StatusController(
      fetcher: () async => const SystemStatus(
        tier: 'gpu',
        gpuOnline: true,
        model: 'qwen2.5:7b-instruct',
      ),
      initial: StatusSnapshot.fromStatus(
        const SystemStatus(
          tier: 'gpu',
          gpuOnline: true,
          model: 'qwen2.5:7b-instruct',
        ),
      ),
    );

Widget _wrap(AiBackend backend) => MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => ChatController(backend)..connect(),
        ),
        ChangeNotifierProvider<StatusController>(
          create: (_) => _onlineStatus(),
        ),
      ],
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        home: const ChatScreen(),
      ),
    );

/// Pump a fixed budget of frames. The status banner's dot pulses perpetually,
/// so pumpAndSettle would never return; a bounded, deterministic sequence of
/// pumps both lets one-shot animations (fade-in, scroll) finish and keeps the
/// captured frame reproducible for goldens.
Future<void> _settleBounded(WidgetTester tester,
    {int frames = 60, int stepMs = 16}) async {
  for (var i = 0; i < frames; i++) {
    await tester.pump(Duration(milliseconds: stepMs));
  }
}

/// Boot the app and let one-shot animations run (bounded; see [_settleBounded]).
Future<void> _boot(WidgetTester tester, AiBackend backend) async {
  tester.view.physicalSize = _viewport;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(_wrap(backend));
  await _settleBounded(tester);
}

/// Boot using fixed-duration pumps - used when the backend never completes
/// (paused stream) so pumpAndSettle would block forever.
Future<void> _bootFixed(WidgetTester tester, AiBackend backend) async {
  tester.view.physicalSize = _viewport;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(_wrap(backend));
  // Allow the fade-in animation (500 ms) plus async gaps to run.
  await tester.pump(const Duration(milliseconds: 600));
}

Future<void> _send(WidgetTester tester, String text) async {
  await tester.enterText(find.byType(TextField), text);
  await tester.pump();
  await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
}

// ---------------------------------------------------------------------------
// Screenshot tests
// ---------------------------------------------------------------------------

void main() {
  testWidgets('screenshot: empty / welcome state', (tester) async {
    await _boot(tester, _FakeBackend());

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('../docs/screenshot-01-empty.png'),
    );
  });

  testWidgets('screenshot: streaming (mid-response with blinking caret)',
      (tester) async {
    await _bootFixed(tester, _PausedFakeBackend());
    await _send(tester, 'How do stateless services scale?');

    // Pump enough frames for the send to dispatch and the first token to land.
    for (var i = 0; i < 30; i++) {
      await tester.pump(const Duration(milliseconds: 16));
    }

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('../docs/screenshot-02-streaming.png'),
    );
  });

  testWidgets('screenshot: complete answer with citations', (tester) async {
    await _boot(tester, _FakeBackend());
    await _send(tester, 'How do stateless services scale?');
    await _settleBounded(tester);

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('../docs/screenshot-03-answer.png'),
    );
  });
}
