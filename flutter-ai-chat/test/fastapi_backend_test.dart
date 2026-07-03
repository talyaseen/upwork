import 'dart:convert';

import 'package:flutter_ai_chat/models/chat_artifact.dart';
import 'package:flutter_ai_chat/models/chat_stream_event.dart';
import 'package:flutter_ai_chat/models/conversation_turn.dart';
import 'package:flutter_ai_chat/services/backend_exception.dart';
import 'package:flutter_ai_chat/services/fastapi_backend.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// All tests here use a MockClient, so they NEVER touch the real backend, the
/// real LLM or any network. This is the mandatory mocked-by-default posture:
/// the /chat SSE stream is faked in-memory, including being split across byte
/// chunks to prove the parser reassembles frames correctly.
void main() {
  const base = 'http://test.local';

  FastApiBackend backendWith(http.Client client) => FastApiBackend(
        baseUrl: base,
        username: 'demo_visitor',
        password: 'demo-pass-123',
        client: client,
      );

  // A buffered JSON response (for the auth handshake), expressed as a stream.
  http.StreamedResponse jsonResponse(String body, int status) =>
      http.StreamedResponse(
        Stream.value(utf8.encode(body)),
        status,
        headers: {'content-type': 'application/json'},
      );

  // An SSE response whose body is delivered as the given byte chunks, so tests
  // can split a single event across two network reads.
  http.StreamedResponse sseResponse(List<String> chunks, {int status = 200}) =>
      http.StreamedResponse(
        Stream.fromIterable(chunks.map(utf8.encode)),
        status,
        headers: {'content-type': 'text/event-stream'},
      );

  String frame(String event, Object data) =>
      'event: $event\ndata: ${jsonEncode(data)}\n\n';

  group('authenticate', () {
    test('registers (201) then logs in and caches the token', () async {
      final paths = <String>[];
      final client = MockClient((req) async {
        paths.add(req.url.path);
        if (req.url.path == '/auth/register') {
          return http.Response(
            jsonEncode({'id': 1, 'username': 'demo_visitor'}),
            201,
          );
        }
        if (req.url.path == '/auth/login') {
          expect(req.headers['content-type'],
              contains('application/x-www-form-urlencoded'));
          expect(req.body, contains('username=demo_visitor'));
          return http.Response(
            jsonEncode({'access_token': 'jwt-abc', 'token_type': 'bearer'}),
            200,
          );
        }
        return http.Response('not found', 404);
      });

      final backend = backendWith(client);
      await backend.authenticate();

      expect(backend.isAuthenticated, isTrue);
      expect(paths, containsAll(['/auth/register', '/auth/login']));
    });

    test('treats an existing account (409) as success', () async {
      final client = MockClient((req) async {
        if (req.url.path == '/auth/register') {
          return http.Response('conflict', 409);
        }
        return http.Response(jsonEncode({'access_token': 'jwt-xyz'}), 200);
      });

      final backend = backendWith(client);
      await backend.authenticate();
      expect(backend.isAuthenticated, isTrue);
    });

    test('throws an auth BackendException when login fails', () async {
      final client = MockClient((req) async {
        if (req.url.path == '/auth/register') {
          return http.Response('', 409);
        }
        return http.Response('bad creds', 401);
      });

      final backend = backendWith(client);
      expect(
        () => backend.authenticate(),
        throwsA(isA<BackendException>().having((e) => e.isAuth, 'isAuth', true)),
      );
    });
  });

  group('chat (SSE streaming)', () {
    test(
        'auto-authenticates, sends a bearer token and JSON body, and streams '
        'metadata citations, tokens, then done', () async {
      String? sentAuthHeader;
      Map<String, dynamic>? sentBody;
      final client = MockClient.streaming((req, bodyStream) async {
        switch (req.url.path) {
          case '/auth/register':
            return jsonResponse('', 409);
          case '/auth/login':
            return jsonResponse(jsonEncode({'access_token': 'jwt-tok'}), 200);
          case '/chat':
            sentAuthHeader = req.headers['authorization'];
            sentBody = jsonDecode(await bodyStream.bytesToString())
                as Map<String, dynamic>;
            return sseResponse([
              frame('metadata', {
                'model': 'qwen2.5:7b-instruct',
                'retrieved': 1,
                'citations': [
                  {
                    'document_id': 2,
                    'document_title': 'Stateless services',
                    'chunk_id': 5,
                    'text': 'Any instance can handle any request.',
                    'score': 0.71,
                  }
                ],
              }),
              frame('token', {'text': 'Stateless '}),
              frame('token', {'text': 'services '}),
              frame('token', {'text': 'scale horizontally.'}),
              frame('done', {'finish_reason': 'stop'}),
            ]);
        }
        return jsonResponse('not found', 404);
      });

      final backend = backendWith(client);
      final events = await backend
          .chat(message: 'why scale?', history: const [])
          .toList();

      expect(sentAuthHeader, 'Bearer jwt-tok');
      expect(sentBody!['message'], 'why scale?');
      expect(sentBody!['history'], isEmpty);

      final metadata = events.first as ChatMetadata;
      expect(metadata.model, 'qwen2.5:7b-instruct');
      expect(metadata.citations, hasLength(1));
      expect(metadata.citations.first.documentTitle, 'Stateless services');
      expect(metadata.citations.first.relevancePercent, 71);

      final answer =
          events.whereType<ChatToken>().map((t) => t.text).join();
      expect(answer, 'Stateless services scale horizontally.');

      expect(events.last, isA<ChatDone>());
      expect((events.last as ChatDone).finishReason, 'stop');
    });

    // REGRESSION PIN (active-skill reflection): the backend now AUTO-ROUTES each
    // turn to a skill and reports the one it actually ran on the metadata frame
    // via a new `skill` field (per-message, independent of the client's selected
    // mode). The parser had no `skill` case, so ChatMetadata.skill was always
    // null and the UI could never reflect the routed skill. This decodes the
    // exact wire shape; it fails on a parser that drops the field.
    test('decodes the routed skill from the metadata frame', () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          return sseResponse([
            frame('metadata', {
              'model': 'm',
              'retrieved': 0,
              // The user had "qa" selected, but the backend routed this turn to
              // code-review from the message content and reports that here.
              'skill': 'code-review',
              'citations': <dynamic>[],
            }),
            frame('token', {'text': 'Reviewed.'}),
            frame('done', {'finish_reason': 'stop'}),
          ]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      final events =
          await backend.chat(message: 'review this', history: const []).toList();

      final metadata = events.whereType<ChatMetadata>().single;
      expect(metadata.skill, 'code-review');
    });

    test('leaves the routed skill null when the metadata frame omits it',
        () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          return sseResponse([
            frame('metadata',
                {'model': 'm', 'retrieved': 0, 'citations': <dynamic>[]}),
            frame('done', {'finish_reason': 'stop'}),
          ]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      final events =
          await backend.chat(message: 'q', history: const []).toList();
      expect(events.whereType<ChatMetadata>().single.skill, isNull);
    });

    test('reassembles a token frame split across two byte chunks', () async {
      final full = frame('token', {'text': 'duplicate charges happen'});
      final split = full.length ~/ 2;
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          return sseResponse([
            full.substring(0, split),
            full.substring(split) + frame('done', {'finish_reason': 'stop'}),
          ]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      final events =
          await backend.chat(message: 'q', history: const []).toList();
      final token = events.whereType<ChatToken>().single;
      expect(token.text, 'duplicate charges happen');
    });

    // REGRESSION PIN: the frame shapes below are copied verbatim from the
    // REAL FastAPI backend's wire contract - see
    // `fastapi-ai-devtools-demo/app/routers/chat.py`'s `event: artifact` yield
    // and `app/schemas/chat.py`'s `ChatArtifactEvent` (also asserted in the
    // backend's own `tests/test_skills.py`). The backend sends `kind` (never
    // `type`) and puts EVERY artifact's canonical text in `source` (there is
    // no `markdown` key on the wire, even for the code-review skill). An
    // earlier version of `ChatArtifact.fromJson` read `json['type']`, which
    // the backend never sends, so `artifact.kind` silently decoded as
    // [ArtifactKind.unknown] for every real artifact - `isDiagram` was always
    // false, so a Mermaid diagram artifact never rendered as a diagram in the
    // UI (see the fix in `lib/models/chat_artifact.dart`). This test fails on
    // that buggy parser and passes once it reads `kind`.
    test('parses a real-shape mermaid artifact frame (no pre-rendered SVG, '
        'the default production config)', () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          return sseResponse([
            frame('artifact', {
              'kind': 'mermaid',
              'format': 'mermaid',
              'source': 'graph TD; A-->B',
              'svg': null,
              'downloads': ['pdf', 'svg', 'png', 'mmd'],
            }),
            frame('token', {'text': 'Here is the diagram.'}),
            frame('done', {'finish_reason': 'stop'}),
          ]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      final events =
          await backend.chat(message: 'diagram?', history: const []).toList();

      final artifactEvent = events.whereType<ChatArtifactEvent>().single;
      final artifact = artifactEvent.artifact;
      expect(artifact.kind, ArtifactKind.mermaid);
      expect(artifact.isDiagram, isTrue);
      expect(artifact.source, 'graph TD; A-->B');
      expect(artifact.hasSvg, isFalse);
    });

    test('parses a real-shape code-review artifact frame (review body lives '
        'in `source`, there is no `markdown` key on the wire)', () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          return sseResponse([
            frame('artifact', {
              'kind': 'markdown',
              'format': 'markdown',
              'source': '## Findings\n- Not idempotent',
              'svg': null,
              'downloads': ['pdf', 'md'],
            }),
            frame('done', {'finish_reason': 'stop'}),
          ]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      final events =
          await backend.chat(message: 'review', history: const []).toList();

      final artifact = events.whereType<ChatArtifactEvent>().single.artifact;
      expect(artifact.kind, ArtifactKind.markdown);
      expect(artifact.isDiagram, isFalse);
      expect(artifact.source, contains('Findings'));
      expect(artifact.hasSvg, isFalse);
    });

    test('surfaces an error event gracefully (LLM unreachable)', () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          return sseResponse([
            frame('metadata',
                {'model': 'm', 'retrieved': 0, 'citations': <dynamic>[]}),
            frame('error',
                {'message': 'The local LLM is unreachable.', 'type': 'ConnError'}),
            frame('done', {'finish_reason': 'error'}),
          ]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      final events =
          await backend.chat(message: 'q', history: const []).toList();
      final error = events.whereType<ChatStreamError>().single;
      expect(error.message, 'The local LLM is unreachable.');
      expect(error.type, 'ConnError');
      expect((events.last as ChatDone).finishReason, 'error');
    });

    test('serialises prior turns and top_k into the request body', () async {
      Map<String, dynamic>? sentBody;
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          sentBody = jsonDecode(await bodyStream.bytesToString())
              as Map<String, dynamic>;
          return sseResponse([frame('done', {'finish_reason': 'stop'})]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      await backend.chat(
        message: 'and how do I make it scale safely?',
        history: const [
          ConversationTurn(role: 'user', content: 'I get duplicate charges.'),
          ConversationTurn(
              role: 'assistant', content: 'Your worker is not idempotent.'),
        ],
        topK: 3,
      ).toList();

      final history = sentBody!['history'] as List<dynamic>;
      expect(history, hasLength(2));
      expect(history.first, {'role': 'user', 'content': 'I get duplicate charges.'});
      expect(history.last['role'], 'assistant');
      expect(sentBody!['top_k'], 3);
    });

    test('includes session_id in the request body when supplied', () async {
      Map<String, dynamic>? sentBody;
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          sentBody = jsonDecode(await bodyStream.bytesToString())
              as Map<String, dynamic>;
          return sseResponse([frame('done', {'finish_reason': 'stop'})]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      await backend
          .chat(message: 'q', history: const [], sessionId: 'abc123')
          .toList();

      expect(sentBody!['session_id'], 'abc123');
    });

    test('omits session_id from the request body when not supplied',
        () async {
      Map<String, dynamic>? sentBody;
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          sentBody = jsonDecode(await bodyStream.bytesToString())
              as Map<String, dynamic>;
          return sseResponse([frame('done', {'finish_reason': 'stop'})]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      await backend.chat(message: 'q', history: const []).toList();

      expect(sentBody!.containsKey('session_id'), isFalse);
    });

    test('surfaces a non-200 chat response as a BackendException', () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') return sseResponse(['boom'], status: 500);
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      expect(
        () => backend.chat(message: 'q', history: const []).toList(),
        throwsA(isA<BackendException>()),
      );
    });

    test('clears the token and reports an auth error on a 401', () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') return sseResponse(['nope'], status: 401);
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      await expectLater(
        () => backend.chat(message: 'q', history: const []).toList(),
        throwsA(
            isA<BackendException>().having((e) => e.isAuth, 'isAuth', true)),
      );
      expect(backend.isAuthenticated, isFalse);
    });

    // REGRESSION PIN (FE C2): the backend, on a full admission queue, streams a
    // single `busy` frame then `done` (finish_reason "busy") - see
    // `fastapi-ai-devtools-demo/app/routers/chat.py`'s QueueFull branch. The
    // parser had no `busy` case, so the frame was silently dropped; the
    // controller then saw zero tokens and told the user "no grounded answer".
    // This decodes the exact wire shape into a distinct [ChatBusy].
    test('decodes a busy frame (server at capacity) as a ChatBusy event',
        () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          return sseResponse([
            frame('busy', {
              'message': 'The demo is at capacity right now. Please try '
                  'again in a few seconds.',
              'retry_after_seconds': 5,
            }),
            frame('done', {'finish_reason': 'busy'}),
          ]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      final events =
          await backend.chat(message: 'q', history: const []).toList();

      final busy = events.whereType<ChatBusy>().single;
      expect(busy.message, contains('capacity'));
      expect(busy.retryAfterSeconds, 5);
      expect((events.last as ChatDone).finishReason, 'busy');
    });

    // REGRESSION PIN (FE C3): the OFFLINE path (GPU yielded to training) streams
    // metadata + a `notice` frame + done (finish_reason "offline") - see
    // chat_service.py's `is_offline` branch. The parser dropped the `notice`
    // frame, so an offline demo also fell into the misleading "no grounded
    // answer" copy. This decodes the notice into a distinct [ChatNotice].
    test('decodes a notice frame (demo offline) as a ChatNotice event',
        () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          return sseResponse([
            frame('metadata', {
              'model': 'offline',
              'retrieved': 0,
              'backend_tier': 'offline',
              'notice': null,
              'citations': <dynamic>[],
            }),
            frame('notice', {
              'message': 'The live demo is paused right now (the GPU is '
                  'training).',
              'model': 'offline',
              'backend_tier': 'offline',
            }),
            frame('done', {'finish_reason': 'offline'}),
          ]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      final events =
          await backend.chat(message: 'q', history: const []).toList();

      final notice = events.whereType<ChatNotice>().single;
      expect(notice.message, contains('paused'));
      expect((events.last as ChatDone).finishReason, 'offline');
    });

    // REGRESSION PIN (FE M1): while waiting for a free slot the backend streams
    // `queue` position frames (chat.py `ticket.wait_for_slot()`), which the
    // parser dropped, leaving a queued visitor with a frozen-looking spinner
    // and no position feedback. This decodes them into ordered [ChatQueue]s.
    test('decodes queue position frames as ordered ChatQueue events', () async {
      final client = MockClient.streaming((req, bodyStream) async {
        if (req.url.path == '/auth/login') {
          return jsonResponse(jsonEncode({'access_token': 't'}), 200);
        }
        if (req.url.path == '/chat') {
          return sseResponse([
            frame('queue', {'position': 2, 'status': 'waiting'}),
            frame('queue', {'position': 1, 'status': 'waiting'}),
            frame('metadata', {
              'model': 'm',
              'retrieved': 0,
              'backend_tier': 'primary-7b-gpu',
              'notice': null,
              'citations': <dynamic>[],
            }),
            frame('token', {'text': 'Answer.'}),
            frame('done', {'finish_reason': 'stop'}),
          ]);
        }
        return jsonResponse('', 409);
      });

      final backend = backendWith(client);
      final events =
          await backend.chat(message: 'q', history: const []).toList();

      final queue = events.whereType<ChatQueue>().toList();
      expect(queue, hasLength(2));
      expect(queue.first.position, 2);
      expect(queue.last.position, 1);
      expect(queue.last.status, 'waiting');
    });
  });
}
