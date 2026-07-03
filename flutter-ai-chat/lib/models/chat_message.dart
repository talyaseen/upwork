import 'package:flutter/foundation.dart';

import 'chat_artifact.dart';
import 'chat_skill.dart';
import 'citation.dart';

enum MessageRole { user, assistant }

/// Delivery state of a single assistant turn, used to drive the UI between
/// the loading indicator, the streaming answer, the finished answer and the
/// several honest "no real answer" outcomes the backend can return.
///
///  * [sending]   - request in flight, no tokens yet (show "retrieving" state),
///  * [queued]    - waiting in the admission queue for a free slot,
///  * [streaming] - tokens are arriving and being appended live,
///  * [complete]  - the answer finished with real model text,
///  * [noAnswer]  - the stream finished cleanly but produced no grounded text;
///                  the shown copy is a client-side hint, NOT model output, so
///                  it is deliberately excluded from the history sent back,
///  * [busy]      - the demo was at capacity; no generation ran,
///  * [offline]   - the live demo is paused (GPU yielded to training), so the
///                  answer is absent or was truncated mid-stream,
///  * [error]     - the turn failed (LLM unreachable / transport error).
///
/// Only [complete] turns are replayed as assistant history (see
/// `ChatController._historyForRequest`); every other terminal state carries
/// either no model text or a client-authored hint that must never be fed back
/// to the model as if it were a real prior answer.
enum MessageStatus {
  sending,
  queued,
  streaming,
  complete,
  noAnswer,
  busy,
  offline,
  error,
}

/// One message in the chat transcript.
///
/// User messages carry only [text]. Assistant messages additionally carry
/// [citations] (the grounding sources) and a [status] so the UI can show a
/// typing indicator while a request is in flight and an error affordance if it
/// fails.
@immutable
class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.role,
    required this.text,
    this.citations = const [],
    this.status = MessageStatus.complete,
    this.grounded = true,
    this.artifacts = const [],
    this.notice,
    this.routedSkill,
  });

  final String id;
  final MessageRole role;
  final String text;
  final List<Citation> citations;
  final MessageStatus status;

  /// False when the assistant could not ground an answer in the corpus.
  final bool grounded;

  /// The skill the backend ACTUALLY routed this assistant turn to (from the
  /// metadata event), which can differ from the mode the user had selected
  /// because the backend auto-routes per-message. Null on user turns and on any
  /// assistant turn the backend did not tag. The bubble renders it as a small
  /// badge so the user is never confused about which skill handled the message.
  final ChatSkill? routedSkill;

  /// Rich artifacts (Mermaid diagrams, code-review documents) attached to an
  /// assistant turn and rendered inline beneath the answer text.
  final List<ChatArtifact> artifacts;

  /// A short out-of-band line the UI shows alongside (or instead of) the
  /// answer for the non-answer states: the queue position while [queued], the
  /// capacity message while [busy], or the "demo paused" notice while
  /// [offline] (including beneath a mid-stream-truncated partial answer). It is
  /// backend-authored operational signal, never part of the answer.
  final String? notice;

  bool get isUser => role == MessageRole.user;

  ChatMessage copyWith({
    String? text,
    List<Citation>? citations,
    MessageStatus? status,
    bool? grounded,
    List<ChatArtifact>? artifacts,
    String? notice,
    ChatSkill? routedSkill,
  }) {
    return ChatMessage(
      id: id,
      role: role,
      text: text ?? this.text,
      citations: citations ?? this.citations,
      status: status ?? this.status,
      grounded: grounded ?? this.grounded,
      artifacts: artifacts ?? this.artifacts,
      notice: notice ?? this.notice,
      // routedSkill is only ever set once (from the metadata event) and never
      // cleared, so the `?? this` fallback is correct here.
      routedSkill: routedSkill ?? this.routedSkill,
    );
  }
}
