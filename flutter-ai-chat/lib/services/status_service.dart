import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/system_status.dart';

/// Fetches the current [SystemStatus] once.
///
/// Modelled as a function type so the state layer depends on a tiny, trivially
/// fakeable seam: tests pass a closure that returns a canned status (or throws
/// to simulate an outage) and never touch the network. Production wires in
/// [HttpStatusFetcher].
typedef StatusFetcher = Future<SystemStatus> Function();

/// Default [StatusFetcher]: a single GET against the public `/status`
/// endpoint on the app's configured backend host.
///
/// The base URL (typically `/api`) is prepended, producing `/api/status` on
/// the wire. The nginx reverse-proxy strips the `/api/` prefix, so FastAPI
/// receives `/status`.
///
/// The base URL is injected from [AppConfig] (never hardcoded), the
/// [http.Client] is injected so tests can supply a mock, and the request is
/// bounded by [timeout] so a hung backend degrades to "unavailable" rather than
/// blocking the poll loop forever. Any failure (transport, timeout, non-200,
/// malformed body) surfaces as a thrown error, which the controller maps to the
/// neutral banner state.
class HttpStatusFetcher {
  HttpStatusFetcher({
    required this.baseUrl,
    http.Client? client,
    this.timeout = const Duration(seconds: 5),
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final Duration timeout;
  final http.Client _client;

  Future<SystemStatus> call() async {
    final res = await _client
        .get(Uri.parse('$baseUrl/status'))
        .timeout(timeout);
    if (res.statusCode != 200) {
      throw http.ClientException(
        'status endpoint returned HTTP ${res.statusCode}',
      );
    }
    final json = jsonDecode(res.body) as Map<String, dynamic>;
    return SystemStatus.fromJson(json);
  }

  void close() => _client.close();
}
