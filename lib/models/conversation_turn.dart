import 'package:flutter/foundation.dart';

/// One prior turn sent back to the backend so follow-up questions have context.
///
/// Mirrors the backend `ChatMessage` request schema: a `role` of `user` or
/// `assistant` and the turn's `content`. The controller builds the history list
/// from the completed transcript and the service serialises it into the `/chat`
/// request body.
@immutable
class ConversationTurn {
  const ConversationTurn({required this.role, required this.content});

  /// Either `user` or `assistant`, matching the backend contract.
  final String role;
  final String content;

  Map<String, String> toJson() => {'role': role, 'content': content};
}
