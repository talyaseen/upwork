import 'dart:async';

import 'package:flutter_ai_chat/models/chat_message.dart';
import 'package:flutter_ai_chat/models/chat_stream_event.dart';
import 'package:flutter_ai_chat/models/conversation_turn.dart';
import 'package:flutter_ai_chat/services/ai_backend.dart';
import 'package:flutter_ai_chat/state/chat_controller.dart';
import 'package:flutter_test/flutter_test.dart';

/// A backend that records the history it was handed and replays a fixed script
/// of events for every `/chat` call, resolving synchronously. Good for the
/// deterministic history / resolution assertions.
class ScriptedBackend implements AiBackend {
  ScriptedBackend(this.script);

  final List<ChatStreamEvent> script;
  List<ConversationTurn>? lastHistory;
  int calls = 0;

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
    calls++;
    lastHistory = history;
    for (final event in script) {
      yield event;
    }
  }
}

/// A backend whose stream the test drives by hand, to exercise cancellation and
/// in-flight state.
class ManualBackend implements AiBackend {
  final StreamController<ChatStreamEvent> controller =
      StreamController<ChatStreamEvent>();

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
      controller.stream;
}

const _answerScript = <ChatStreamEvent>[
  ChatMetadata(model: 'm', retrieved: 0, citations: []),
  ChatToken('An answer.'),
  ChatDone('stop'),
];

void main() {
  group('history for request', () {
    test('caps the history sent to the backend at 20 turns (H1)', () async {
      final backend = ScriptedBackend(_answerScript);
      final controller = ChatController(backend);
      await controller.connect();

      // Each completed exchange adds a user + assistant turn (2). After enough
      // exchanges the unbounded history would exceed the backend's cap of 20
      // and every further send would fail a permanent HTTP 422.
      for (var i = 0; i < 15; i++) {
        await controller.send('question $i');
      }

      // The final request must have carried at most 20 turns...
      expect(backend.lastHistory!.length, 20);
      // ...comprised of the MOST RECENT turns (oldest trimmed off the front).
      expect(backend.lastHistory!.first.content, isNot(contains('question 0')));
      expect(backend.lastHistory!.last.role, 'assistant');
    });

    test(
        'the client-side "no grounded answer" turn is never replayed as '
        'assistant history (L3)', () async {
      // A stream that finishes cleanly with no tokens -> the controller shows a
      // client-authored "no grounded answer" hint. That fabricated text must
      // NOT be sent back as if it were a real model answer.
      final backend = ScriptedBackend(const [
        ChatMetadata(model: 'm', retrieved: 0, citations: []),
        ChatDone('stop'),
      ]);
      final controller = ChatController(backend);
      await controller.connect();

      await controller.send('obscure question');
      expect(controller.messages.last.status, MessageStatus.noAnswer);

      await controller.send('follow up');

      // The follow-up history contains only the prior USER turn, not the
      // fabricated assistant hint.
      final history = backend.lastHistory!;
      expect(history, hasLength(1));
      expect(history.single.role, 'user');
      expect(history.single.content, 'obscure question');
    });
  });

  group('non-answer resolution', () {
    test('a busy stream resolves to the busy state, not a completed answer',
        () async {
      final backend = ScriptedBackend(const [
        ChatBusy(message: 'At capacity.'),
        ChatDone('busy'),
      ]);
      final controller = ChatController(backend);
      await controller.connect();

      await controller.send('q');

      final last = controller.messages.last;
      expect(last.status, MessageStatus.busy);
      expect(last.notice, contains('capacity'));
      // Busy turns are not history either.
      await controller.send('q2');
      expect(backend.lastHistory, hasLength(1));
      expect(backend.lastHistory!.single.role, 'user');
    });

    test(
        'a context-overflow error surfaces the specific notice, not the '
        'generic "could not complete" copy', () async {
      // The backend context-overflow path (chat_service.py) emits a notice with
      // the actionable CONTEXT_TOO_LONG message, then done(finish_reason
      // "error"). The streamError branch previously showed only the generic
      // "could not complete" fallback and DROPPED that specific notice.
      const overflowNotice =
          'Your message is too long for the model context. Please shorten it.';
      final backend = ScriptedBackend(const [
        ChatMetadata(model: 'm', retrieved: 0, citations: []),
        ChatNotice(message: overflowNotice),
        ChatDone('error'),
      ]);
      final controller = ChatController(backend);
      await controller.connect();

      await controller.send('a very long question');

      final last = controller.messages.last;
      expect(last.status, MessageStatus.error);
      expect(last.text, overflowNotice);
      expect(last.text, isNot(contains('could not complete')));
    });
  });

  group('cancellation', () {
    test(
        'startNewChat cancels an in-flight send and re-enables the composer '
        'immediately (M2)', () async {
      final backend = ManualBackend();
      final controller = ChatController(backend);
      await controller.connect();

      final inFlight = controller.send('hi');
      await pumpEventQueue();

      expect(controller.isSending, isTrue);
      expect(controller.messages, isNotEmpty);

      controller.startNewChat();

      // Composer is usable again at once, and the transcript is cleared.
      expect(controller.isSending, isFalse);
      expect(controller.messages, isEmpty);

      // A late event from the abandoned stream must not resurrect a bubble or
      // flip the sending flag back.
      backend.controller.add(const ChatToken('late token'));
      await backend.controller.close();
      await inFlight;

      expect(controller.isSending, isFalse);
      expect(controller.messages, isEmpty);
    });

    test('a queue event surfaces the queued state with the position', () async {
      final backend = ManualBackend();
      final controller = ChatController(backend);
      await controller.connect();

      final inFlight = controller.send('hi');
      backend.controller.add(const ChatQueue(position: 4, status: 'waiting'));
      await pumpEventQueue();

      final pending = controller.messages.last;
      expect(pending.status, MessageStatus.queued);
      expect(pending.notice, contains('4'));

      backend.controller.add(const ChatMetadata(
        model: 'm',
        retrieved: 0,
        citations: [],
      ));
      backend.controller.add(const ChatToken('Answer.'));
      backend.controller.add(const ChatDone('stop'));
      await backend.controller.close();
      await inFlight;

      expect(controller.messages.last.status, MessageStatus.complete);
    });
  });
}
