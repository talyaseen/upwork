import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/chat_artifact.dart';
import '../models/chat_stream_event.dart';
import '../models/citation.dart';
import '../models/conversation_turn.dart';
import 'ai_backend.dart';
import 'backend_exception.dart';

/// [AiBackend] backed by the local FastAPI conversational service.
///
/// Responsibilities, all kept out of the UI:
///  * transparently provision the demo account (register-or-login),
///  * cache the JWT and attach it as a bearer token on every call,
///  * open the streamed `/chat` endpoint and parse its Server-Sent Events into
///    the app's [ChatStreamEvent] family,
///  * translate transport and HTTP errors into [BackendException].
///
/// The streamed response is read incrementally: on Flutter web the default
/// `http.Client` is backed by the Fetch API, whose response body streams chunk
/// by chunk, so tokens reach the UI as they are generated rather than all at
/// the end. The [http.Client] is injected so tests can supply a mock and never
/// touch a real network. The base URL is injected from config, never hardcoded.
class FastApiBackend implements AiBackend {
  FastApiBackend({
    required this.baseUrl,
    required this.username,
    required this.password,
    http.Client? client,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final String username;
  final String password;
  final http.Client _client;

  /// Cached bearer token. In-memory is appropriate for a transparent demo
  /// account; a production build would persist this in secure storage and add
  /// refresh handling, which stays fully contained in this class.
  String? _token;

  bool get isAuthenticated => _token != null;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  @override
  Future<void> authenticate() async {
    // Idempotent provisioning: register the demo user if it does not exist
    // yet, then log in. A 409 simply means a previous visitor already created
    // it, which is the normal steady state.
    await _ensureDemoUser();
    _token = await _login();
  }

  Future<void> _ensureDemoUser() async {
    try {
      final res = await _client.post(
        _uri('/auth/register'),
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );
      // 201 = created, 409 = already exists. Both are success for our purpose.
      if (res.statusCode != 201 && res.statusCode != 409) {
        throw BackendException(
          'Could not provision the demo account (HTTP ${res.statusCode}).',
          isAuth: true,
        );
      }
    } on http.ClientException catch (e) {
      throw BackendException(_networkMessage(e), isAuth: true);
    }
  }

  Future<String> _login() async {
    try {
      // The backend's /auth/login uses OAuth2 password flow, so credentials
      // are sent as form fields rather than JSON.
      final res = await _client.post(
        _uri('/auth/login'),
        headers: const {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: {'username': username, 'password': password},
      );
      if (res.statusCode != 200) {
        throw BackendException(
          'Sign-in failed (HTTP ${res.statusCode}).',
          isAuth: true,
        );
      }
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final token = data['access_token'] as String?;
      if (token == null || token.isEmpty) {
        throw const BackendException(
          'Sign-in succeeded but no token was returned.',
          isAuth: true,
        );
      }
      return token;
    } on http.ClientException catch (e) {
      throw BackendException(_networkMessage(e), isAuth: true);
    } on FormatException {
      throw const BackendException(
        'The server returned an unexpected sign-in response.',
        isAuth: true,
      );
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
    if (_token == null) {
      // Lazily authenticate so a caller can use the backend without ordering
      // the calls by hand.
      await authenticate();
    }

    final request = http.Request('POST', _uri('/chat'))
      ..headers.addAll({
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'Authorization': 'Bearer $_token',
      })
      ..body = jsonEncode({
        'message': message,
        'history': history.map((t) => t.toJson()).toList(growable: false),
        if (topK != null) 'top_k': topK,
        if (sessionId != null) 'session_id': sessionId,
        if (skill != null) 'skill': skill,
      });

    final http.StreamedResponse response;
    try {
      response = await _client.send(request);
    } on http.ClientException catch (e) {
      throw BackendException(_networkMessage(e));
    }

    if (response.statusCode == 401) {
      // Token expired or rejected: clear it so the next attempt re-auths.
      _token = null;
      throw const BackendException(
        'Your session expired. Please try again.',
        isAuth: true,
      );
    }
    if (response.statusCode != 200) {
      throw BackendException(
        'The assistant could not answer right now (HTTP '
        '${response.statusCode}).',
      );
    }

    try {
      yield* _parseSse(response.stream);
    } on http.ClientException catch (e) {
      throw BackendException(_networkMessage(e));
    }
  }

  /// Parse a Server-Sent Events byte stream into [ChatStreamEvent]s.
  ///
  /// SSE frames are separated by a blank line; within a frame, `event:` names
  /// the event and `data:` carries its JSON payload. The byte stream is decoded
  /// and split into lines, so a single token can arrive split across network
  /// chunks without corrupting the parse.
  Stream<ChatStreamEvent> _parseSse(Stream<List<int>> byteStream) async* {
    var eventName = '';
    final data = StringBuffer();

    Stream<String> lines() =>
        byteStream.transform(utf8.decoder).transform(const LineSplitter());

    await for (final line in lines()) {
      if (line.isEmpty) {
        // Blank line terminates the current frame; dispatch and reset.
        final event = _decodeEvent(eventName, data.toString());
        eventName = '';
        data.clear();
        if (event != null) yield event;
        continue;
      }
      if (line.startsWith(':')) continue; // SSE comment / keep-alive.
      if (line.startsWith('event:')) {
        eventName = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        // A single optional leading space after the colon is part of the SSE
        // framing, not the value. Multiple data lines join with a newline.
        var value = line.substring(5);
        if (value.startsWith(' ')) value = value.substring(1);
        if (data.isNotEmpty) data.write('\n');
        data.write(value);
      }
    }

    // Flush a trailing frame that was not followed by a blank line.
    final event = _decodeEvent(eventName, data.toString());
    if (event != null) yield event;
  }

  ChatStreamEvent? _decodeEvent(String eventName, String rawData) {
    if (rawData.isEmpty) return null;
    final Map<String, dynamic> json;
    try {
      json = jsonDecode(rawData) as Map<String, dynamic>;
    } on FormatException {
      // A malformed frame is skipped rather than aborting the whole stream.
      return null;
    }

    switch (eventName) {
      case 'metadata':
        final rawCitations = json['citations'] as List<dynamic>? ?? const [];
        return ChatMetadata(
          model: json['model'] as String? ?? '',
          retrieved: (json['retrieved'] as num?)?.toInt() ?? 0,
          // The backend auto-routes each turn to a skill and reports the one it
          // actually ran here, so the UI can reflect it (badge + selector sync).
          skill: json['skill'] as String?,
          citations: rawCitations
              .map((c) => Citation.fromJson(c as Map<String, dynamic>))
              .toList(growable: false),
        );
      case 'token':
        return ChatToken(json['text'] as String? ?? '');
      case 'artifact':
        return ChatArtifactEvent(ChatArtifact.fromJson(json));
      case 'done':
        return ChatDone(json['finish_reason'] as String? ?? 'stop');
      case 'error':
        return ChatStreamError(
          message: json['message'] as String? ??
              'The assistant hit an error generating the response.',
          type: json['type'] as String? ?? 'error',
        );
      case 'busy':
        // Admission queue full: no generation ran. Distinct from an ungrounded
        // answer - surface the server's own capacity message and retry hint.
        return ChatBusy(
          message: json['message'] as String? ??
              'The demo is at capacity right now. Please try again in a '
                  'few seconds.',
          retryAfterSeconds: (json['retry_after_seconds'] as num?)?.toInt(),
        );
      case 'notice':
        // The live demo went offline (GPU yielded to training). Carries a
        // user-facing message; it is not, and never grounds, an answer.
        return ChatNotice(
          message: json['message'] as String? ??
              'The live demo is paused right now. Please try again shortly.',
        );
      case 'queue':
        // Waiting-in-line position update; shown while a slot is pending.
        return ChatQueue(
          position: (json['position'] as num?)?.toInt() ?? 0,
          status: json['status'] as String? ?? 'waiting',
        );
      default:
        return null;
    }
  }

  String _networkMessage(Object error) =>
      'Could not reach the assistant backend at $baseUrl. '
      'Is the service running?';

  /// Release the underlying client. Call when the backend is disposed.
  void close() => _client.close();
}
