import '../models/chat_stream_event.dart';
import '../models/conversation_turn.dart';

/// The boundary between the app and whatever AI service answers questions.
///
/// The UI and state layers depend only on this interface, never on a concrete
/// HTTP client, a base URL or a vendor SDK. Today the single implementation is
/// [FastApiBackend] (see `fastapi_backend.dart`), which talks to the local
/// FastAPI conversational service over a streamed, JWT-protected `/chat`
/// endpoint (Server-Sent Events).
///
/// ---------------------------------------------------------------------------
/// SWAPPING TO OPENAI
/// ---------------------------------------------------------------------------
/// Because everything above this line depends on `AiBackend` and nothing else,
/// moving to OpenAI is a single, localized change: add one class, e.g.
///
/// ```dart
/// class OpenAiBackend implements AiBackend {
///   OpenAiBackend(this._client, {required this.apiKey});
///   final http.Client _client;
///   final String apiKey; // injected from secure config, never committed
///
///   @override
///   Future<void> authenticate() async {
///     // OpenAI uses a bearer API key, so there is no register/login step.
///   }
///
///   @override
///   Stream<ChatStreamEvent> chat({
///     required String message,
///     required List<ConversationTurn> history,
///     int? topK,
///   }) async* {
///     // POST https://api.openai.com/v1/chat/completions with
///     // Authorization: Bearer $apiKey and "stream": true. OpenAI already
///     // speaks the same Server-Sent Events wire format, so the SSE parsing
///     // is identical: map each delta chunk to a ChatToken and finalize on
///     // the [DONE] sentinel. (Citations would come from a tool/file-search
///     // step mapped into a leading ChatMetadata event.)
///   }
/// }
/// ```
///
/// Then change exactly one wiring line where the backend is constructed
/// (in `main.dart`) from `FastApiBackend(...)` to `OpenAiBackend(...)`. No UI,
/// state, model or test code changes. This demo deliberately does NOT call
/// OpenAI or any paid API anywhere; the note above documents the future swap.
abstract class AiBackend {
  /// Establish a session if the backend needs one.
  ///
  /// For [FastApiBackend] this transparently provisions the demo account
  /// (register-or-login) and caches the JWT for subsequent calls. An
  /// implementation that authenticates per-request (such as an API-key vendor)
  /// may make this a no-op.
  Future<void> authenticate();

  /// Send a conversational [message] and stream the grounded answer back.
  ///
  /// [history] carries the prior turns (oldest first) so the backend can answer
  /// follow-ups in context - this is the ONLY thing the backend uses to build
  /// the model's context; it keeps no server-side conversation memory of its
  /// own. [topK] optionally overrides how many corpus chunks are retrieved as
  /// grounding context. [sessionId] is an opaque per-conversation id: the
  /// backend does not use it for context (that is [history]'s job), only for
  /// its own per-session learning trace and durable conversation audit log, so
  /// rotating it (see `ChatController.startNewChat`) cleanly separates one
  /// conversation's log entries from the next.
  ///
  /// Yields a [ChatMetadata] event first (the citations, up front), then a run
  /// of [ChatToken] events to be concatenated into the answer, then a terminal
  /// [ChatDone]. A [ChatStreamError] is yielded if the language model fails.
  ///
  /// [skill] explicitly selects which backend skill answers this turn: 'qa'
  /// (default grounded RAG), 'code-review' or 'mermaid' (see
  /// `app/services/skills.py` and `GET /skills` on the FastAPI service).
  /// Omit or pass null to let the backend fall back to its default ('qa').
  ///
  /// Throws [BackendException] on a transport or protocol failure that happens
  /// before the stream is established (for example a rejected token).
  Stream<ChatStreamEvent> chat({
    required String message,
    required List<ConversationTurn> history,
    int? topK,
    String? sessionId,
    String? skill,
  });
}
