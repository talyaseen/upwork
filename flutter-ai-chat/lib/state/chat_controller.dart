import 'dart:math';

import 'package:flutter/foundation.dart';

import '../models/chat_message.dart';
import '../models/chat_skill.dart';
import '../models/chat_stream_event.dart';
import '../models/conversation_turn.dart';
import '../services/ai_backend.dart';
import '../services/backend_exception.dart';

/// A short opaque per-conversation id (hex-encoded random bytes). Not a
/// security token - just a boundary marker the backend uses to group its own
/// per-session learning trace and audit log, so it does not need to be
/// cryptographically unpredictable, only unique enough to not collide across
/// visits from the same demo account.
String _generateSessionId() {
  final rand = Random();
  final bytes = List<int>.generate(16, (_) => rand.nextInt(256));
  return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
}

/// Connection state of the transparent demo session.
enum SessionStatus { connecting, ready, failed }

/// Owns the chat transcript and the backend session, and exposes a small,
/// UI-friendly surface. Depends only on the [AiBackend] abstraction, so it is
/// identical whether the backend is FastAPI today or OpenAI tomorrow, and it is
/// trivially testable with a fake backend.
class ChatController extends ChangeNotifier {
  ChatController(this._backend);

  final AiBackend _backend;

  final List<ChatMessage> _messages = <ChatMessage>[];
  List<ChatMessage> get messages => List.unmodifiable(_messages);

  SessionStatus _session = SessionStatus.connecting;
  SessionStatus get session => _session;

  String? _sessionError;
  String? get sessionError => _sessionError;

  bool _isSending = false;
  bool get isSending => _isSending;

  bool get hasMessages => _messages.isNotEmpty;

  /// Backend history cap: the FastAPI `/chat` request rejects a `history`
  /// longer than 20 turns (`ChatRequest.history` max_length). Without a
  /// client-side cap every send after ~10 exchanges fails a permanent HTTP 422
  /// that Retry can never clear, so the transcript is trimmed to the most
  /// recent [_maxHistoryTurns] turns before each request.
  static const int _maxHistoryTurns = 20;

  /// Monotonic id of the in-flight [send]. Bumped by a new [send] and by
  /// [startNewChat] so a superseded/abandoned stream can detect it is no longer
  /// the current turn and bow out (break its await-loop, skip its resolution,
  /// and leave [_isSending] alone) instead of writing into a cleared transcript
  /// or pinning the composer disabled after the user moved on.
  int _sendGeneration = 0;

  int _counter = 0;
  String _nextId() => 'm${_counter++}';

  /// The explicitly selected skill for the NEXT message (see [ChatSkill]).
  /// Defaults to plain grounded Q&A, matches the backend's own default
  /// (`SkillRegistry.default_skill`), and is sent verbatim as `skill` on every
  /// `/chat` call so the right backend behaviour fires regardless of wording.
  ChatSkill _skill = ChatSkill.qa;
  ChatSkill get skill => _skill;

  /// Switch the active skill (e.g. from the mode selector). Takes effect on
  /// the next [send] call; does not touch the existing transcript.
  void setSkill(ChatSkill skill) {
    if (skill == _skill) return;
    _skill = skill;
    notifyListeners();
  }

  /// Opaque id for the CURRENT conversation, sent with every `/chat` call.
  /// Model CONTEXT never depends on this (the backend keeps no server-side
  /// conversation memory - see [_historyForRequest] and `AiBackend.chat`); it
  /// only scopes the backend's own per-session learning trace and durable
  /// conversation audit log. Rotated by [startNewChat].
  String _sessionId = _generateSessionId();
  String get sessionId => _sessionId;

  /// Establish the transparent demo session on startup. Safe to retry.
  Future<void> connect() async {
    _session = SessionStatus.connecting;
    _sessionError = null;
    notifyListeners();
    try {
      await _backend.authenticate();
      _session = SessionStatus.ready;
    } on BackendException catch (e) {
      _session = SessionStatus.failed;
      _sessionError = e.message;
    } catch (_) {
      _session = SessionStatus.failed;
      _sessionError = 'Something went wrong while connecting.';
    }
    notifyListeners();
  }

  /// Send a message through the backend and stream the answer in.
  ///
  /// Appends the user turn immediately, then a placeholder assistant turn in
  /// the `sending` state so the UI can show a "retrieving / thinking"
  /// indicator. As the backend streams Server-Sent Events, the citations are
  /// attached from the leading metadata event and each token is appended live
  /// (typewriter effect). The prior turns are sent as `history` so follow-ups
  /// keep context.
  Future<void> send(String rawText) async {
    final text = rawText.trim();
    if (text.isEmpty || _isSending) return;

    _isSending = true;
    final generation = ++_sendGeneration;
    // Snapshot the conversation BEFORE adding the new turn, so history carries
    // only the prior, completed exchanges.
    final history = _historyForRequest();

    final userMessage = ChatMessage(
      id: _nextId(),
      role: MessageRole.user,
      text: text,
    );
    final pendingId = _nextId();
    final pending = ChatMessage(
      id: pendingId,
      role: MessageRole.assistant,
      text: '',
      status: MessageStatus.sending,
    );
    _messages
      ..add(userMessage)
      ..add(pending);
    notifyListeners();

    final answer = StringBuffer();
    var sawToken = false;
    var sawArtifact = false;
    var streamError = false;
    String? errorMessage;
    // Terminal-state signals distinct from a normal answer (see the honest
    // resolution below). The backend can end a turn without a real answer in
    // several materially different ways; each gets its own UI state and copy
    // instead of the misleading "no grounded answer" catch-all.
    String? busyMessage; // demo at capacity (busy event / finish_reason busy)
    String? noticeMessage; // demo offline (notice event / finish_reason offline)
    String? finishReason;

    try {
      await for (final event in _backend.chat(
        message: text,
        history: history,
        sessionId: _sessionId,
        skill: _skill.id,
      )) {
        // A newer send() or startNewChat() superseded this turn while it was
        // streaming: stop consuming (which cancels the underlying stream) and
        // let the newer generation own the UI.
        if (generation != _sendGeneration) break;
        switch (event) {
          case ChatQueue(:final position):
            // Waiting for a free slot: show honest "in line" feedback instead
            // of a spinner that looks frozen.
            _replace(
              pendingId,
              (m) => m.copyWith(
                status: MessageStatus.queued,
                notice: position > 0
                    ? 'Waiting for an available slot - position $position in '
                        'the queue...'
                    : 'Waiting for an available slot...',
              ),
            );
            notifyListeners();
          case ChatMetadata(:final citations, skill: final routedId):
            // The backend auto-routes each turn and reports which skill it
            // actually ran here. Reflect reality in the UI: tag this reply with
            // the routed skill (rendered as a badge) and sync the selector to
            // what actually ran, so the dropdown never silently mismatches the
            // handled turn - it stays an honest mirror rather than a stale trap.
            final routed = ChatSkill.fromId(routedId);
            if (routed != null && routed != _skill) {
              _skill = routed;
            }
            _replace(
              pendingId,
              (m) => m.copyWith(
                citations: citations,
                grounded: citations.isNotEmpty,
                routedSkill: routed,
                // A queue wait resolved; drop back to the "thinking" state
                // unless tokens have already started arriving.
                status: sawToken
                    ? MessageStatus.streaming
                    : MessageStatus.sending,
              ),
            );
            notifyListeners();
          case ChatToken(:final text):
            if (text.isEmpty) continue;
            sawToken = true;
            answer.write(text);
            _replace(
              pendingId,
              (m) => m.copyWith(
                text: answer.toString(),
                status: MessageStatus.streaming,
              ),
            );
            notifyListeners();
          case ChatArtifactEvent(:final artifact):
            sawArtifact = true;
            _replace(
              pendingId,
              (m) => m.copyWith(artifacts: [...m.artifacts, artifact]),
            );
            notifyListeners();
          case ChatBusy(:final message):
            busyMessage = message;
          case ChatNotice(:final message):
            // May arrive up front (offline at start) or mid-stream (GPU
            // yielded partway); resolution below preserves any partial answer.
            noticeMessage = message;
          case ChatDone(finishReason: final reason):
            finishReason = reason;
            if (reason == 'error') streamError = true;
          case ChatStreamError(:final message):
            streamError = true;
            errorMessage = message;
        }
      }

      // Superseded mid-stream: the pending bubble was cleared by the newer
      // generation, so there is nothing to resolve and _isSending belongs to
      // that newer turn now.
      if (generation != _sendGeneration) return;

      if (streamError) {
        _replace(
          pendingId,
          (m) => m.copyWith(
            // Surface the most specific message available: an explicit stream
            // error string, else a notice the backend emitted before failing
            // (e.g. CONTEXT_TOO_LONG on a context-overflow finish), else the
            // generic fallback. Without the notice fallback the actionable
            // "your message is too long" copy is dropped for the vague default.
            text: errorMessage ??
                noticeMessage ??
                'The assistant could not complete the response. The local '
                    'language model may be unreachable. Please try again.',
            status: MessageStatus.error,
          ),
        );
      } else if (busyMessage != null || finishReason == 'busy') {
        // The demo was at capacity: no generation ran. This is NOT an
        // ungrounded answer - say so honestly and invite a retry.
        _replace(
          pendingId,
          (m) => m.copyWith(
            text: '',
            status: MessageStatus.busy,
            notice: busyMessage ??
                'The demo is at capacity right now. Please try again in a '
                    'few seconds.',
          ),
        );
      } else if (finishReason == 'offline' || noticeMessage != null) {
        // The live demo is paused (GPU yielded to a training window). If tokens
        // had already started, keep the partial answer and flag the truncation
        // rather than silently marking a cut-off reply "complete".
        _replace(
          pendingId,
          (m) => m.copyWith(
            status: MessageStatus.offline,
            notice: noticeMessage ??
                'The live demo is paused right now (the GPU is training). '
                    'Please try again shortly.',
          ),
        );
      } else if (!sawToken && !sawArtifact) {
        // The stream finished cleanly but produced no text and no artifact.
        // The copy below is a client-side hint, so it is stored as [noAnswer]
        // (never [complete]) and is deliberately kept out of the history sent
        // back to the model on the next turn.
        _replace(
          pendingId,
          (m) => m.copyWith(
            text: 'I could not find a grounded answer for that in the '
                'knowledge base. Try rephrasing, or ask about software '
                'architecture, AI engineering or DevOps.',
            status: MessageStatus.noAnswer,
            grounded: false,
          ),
        );
      } else {
        _replace(
          pendingId,
          (m) => m.copyWith(status: MessageStatus.complete),
        );
      }
    } on BackendException catch (e) {
      if (generation != _sendGeneration) return;
      _replace(
        pendingId,
        (m) => m.copyWith(text: e.message, status: MessageStatus.error),
      );
    } catch (_) {
      if (generation != _sendGeneration) return;
      _replace(
        pendingId,
        (m) => m.copyWith(
          text: 'Unexpected error. Please try again.',
          status: MessageStatus.error,
        ),
      );
    } finally {
      // Only the current turn owns the sending flag: a superseded turn must not
      // stomp the newer one's in-flight state.
      if (generation == _sendGeneration) {
        _isSending = false;
        notifyListeners();
      }
    }
  }

  /// Build the conversation history for the next request from the completed
  /// transcript: every user turn, and every assistant turn that finished with
  /// real text. In-flight, empty or failed assistant turns are skipped.
  List<ConversationTurn> _historyForRequest() {
    final turns = <ConversationTurn>[];
    for (final m in _messages) {
      if (m.isUser) {
        turns.add(ConversationTurn(role: 'user', content: m.text));
      } else if (m.status == MessageStatus.complete && m.text.isNotEmpty) {
        // Only genuinely completed model answers are replayed as history.
        // In-flight, empty, failed, busy, offline and the client-authored
        // "no grounded answer" (noAnswer) turns are all skipped, so the model
        // never sees a fabricated hint dressed up as its own prior reply.
        turns.add(ConversationTurn(role: 'assistant', content: m.text));
      }
    }
    // The backend rejects a history longer than the cap, so keep only the most
    // recent turns. Without this, every send past the cap fails a permanent
    // HTTP 422 that Retry cannot clear.
    if (turns.length > _maxHistoryTurns) {
      return turns.sublist(turns.length - _maxHistoryTurns);
    }
    return turns;
  }

  /// Retry the last failed assistant turn by resending the preceding question.
  Future<void> retryLast() async {
    if (_isSending || _messages.isEmpty) return;
    final last = _messages.last;
    // Retry renders not only on a hard error bubble but also on the two "no
    // real answer" backend states - busy (at capacity) and offline (GPU
    // training) - so the gate has to admit all three, otherwise tapping Retry
    // on the flagship's capacity/offline bubble is a dead control.
    const retryable = {
      MessageStatus.error,
      MessageStatus.busy,
      MessageStatus.offline,
    };
    if (!retryable.contains(last.status)) return;
    // Drop the failed assistant turn and the user turn, then resend.
    final question = _messages.length >= 2
        ? _messages[_messages.length - 2].text
        : '';
    _messages.removeLast();
    if (_messages.isNotEmpty && _messages.last.isUser) {
      _messages.removeLast();
    }
    notifyListeners();
    if (question.isNotEmpty) {
      await send(question);
    }
  }

  /// Start a genuinely fresh conversation: clears the visible transcript AND
  /// rotates [sessionId], then notifies listeners.
  ///
  /// This is a REAL reset, not just a UI clear: the next [send] call builds
  /// its `history` from the now-empty [_messages] (see
  /// [_historyForRequest]), so the backend receives an empty history and
  /// therefore has no memory of the prior exchange to ground its answer in -
  /// there is no server-side session store keyed by the old id that would
  /// keep the old conversation silently attached.
  ///
  /// Any request already in flight is CANCELLED, not merely orphaned: bumping
  /// [_sendGeneration] makes the running [send] break its await-loop (which
  /// cancels the underlying stream) and skip its resolution, and the composer
  /// is re-enabled immediately by clearing [_isSending] so the user is never
  /// locked out for the remaining lifetime of a stream they abandoned.
  void startNewChat() {
    _sendGeneration++;
    _isSending = false;
    _messages.clear();
    _sessionId = _generateSessionId();
    notifyListeners();
  }

  void _replace(String id, ChatMessage Function(ChatMessage) update) {
    final index = _messages.indexWhere((m) => m.id == id);
    if (index == -1) return;
    _messages[index] = update(_messages[index]);
  }
}
