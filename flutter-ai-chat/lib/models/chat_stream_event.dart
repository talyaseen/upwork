import 'package:flutter/foundation.dart';

import 'chat_artifact.dart';
import 'citation.dart';

/// One event in the backend's streamed `/chat` response.
///
/// The `/chat` endpoint answers with Server-Sent Events (text/event-stream).
/// The events arrive in a fixed order: a single [ChatMetadata] carrying the
/// grounding citations up front, then many [ChatToken]s that together form the
/// answer, then a terminal [ChatDone]. A [ChatStreamError] is emitted only when
/// the local LLM is unreachable, and is always followed by a done event.
///
/// The service layer maps the raw SSE frames onto this sealed family so the
/// state layer can pattern-match the stream without ever touching the wire
/// format.
@immutable
sealed class ChatStreamEvent {
  const ChatStreamEvent();
}

/// The leading event: the model name, how many chunks were retrieved, and the
/// source citations that ground the answer. Delivered before any tokens so the
/// UI can show the sources while the answer is still streaming.
@immutable
class ChatMetadata extends ChatStreamEvent {
  const ChatMetadata({
    required this.model,
    required this.retrieved,
    required this.citations,
    this.skill,
  });

  final String model;
  final int retrieved;
  final List<Citation> citations;

  /// The wire id of the skill the backend ACTUALLY routed this turn to
  /// (`qa` / `code-review` / `mermaid`), decided per-message from the content
  /// rather than the client's selected mode - which the backend now treats only
  /// as a tiebreaker hint. Null when the backend did not report a routed skill
  /// (e.g. an offline metadata frame). The UI reflects this so the user always
  /// sees which skill handled their message, even when it differs from the
  /// mode they had selected.
  final String? skill;
}

/// An incremental fragment of the answer. Concatenate every [text] in arrival
/// order to build the full reply.
@immutable
class ChatToken extends ChatStreamEvent {
  const ChatToken(this.text);

  final String text;
}

/// A rich artifact a skill attached to the answer (a Mermaid diagram or a
/// code-review Markdown document). Emitted as its own `artifact` SSE frame; the
/// UI renders it inline beneath the answer text and offers downloads.
@immutable
class ChatArtifactEvent extends ChatStreamEvent {
  const ChatArtifactEvent(this.artifact);

  final ChatArtifact artifact;
}

/// The terminal event. [finishReason] is `stop` on success or `error` when the
/// stream ended because of an LLM failure (preceded by a [ChatStreamError]).
@immutable
class ChatDone extends ChatStreamEvent {
  const ChatDone(this.finishReason);

  final String finishReason;
}

/// A graceful, user-readable stream error (the local LLM was unreachable).
@immutable
class ChatStreamError extends ChatStreamEvent {
  const ChatStreamError({required this.message, required this.type});

  final String message;
  final String type;
}

/// The demo is at capacity: the admission queue was full so no generation ran.
/// A `busy` frame carries a human-readable [message] and an optional
/// [retryAfterSeconds] hint, and is the ONLY content event before the terminal
/// `done` (finish_reason `busy`). It must never be conflated with an
/// ungrounded answer - the server simply had no free slot.
@immutable
class ChatBusy extends ChatStreamEvent {
  const ChatBusy({required this.message, this.retryAfterSeconds});

  final String message;
  final int? retryAfterSeconds;
}

/// An out-of-band notice the backend streams when the live demo went OFFLINE
/// (the GPU yielded to a training window), either before any token or partway
/// through an answer. Carries a user-facing [message]; it is not an answer and
/// never grounds one. The stream ends with `done` (finish_reason `offline`).
@immutable
class ChatNotice extends ChatStreamEvent {
  const ChatNotice({required this.message});

  final String message;
}

/// A position update streamed while the request waits for a free generation
/// slot. Emitted zero or more times before metadata; lets the UI show honest
/// "waiting in line" feedback instead of a silent, seemingly-frozen spinner.
@immutable
class ChatQueue extends ChatStreamEvent {
  const ChatQueue({required this.position, required this.status});

  final int position;
  final String status;
}
