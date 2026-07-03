import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/system_status.dart';
import '../services/status_service.dart';

/// How often the banner re-polls `/api/status`. A const so the interval is a
/// single source of truth; 10-30s is the acceptable band for a demo.
const Duration kStatusPollInterval = Duration(seconds: 15);

/// The three visible health states the top banner can show.
enum StatusLevel {
  /// GPU serving tier is up and answering.
  online,

  /// The GPUs are offline (repurposed for training). This backend is GPU-only
  /// with no CPU fallback, so while the status endpoint is reachable, no
  /// answers are being served. A known, amber "down" state - distinct from the
  /// grey "we couldn't reach the endpoint" state below.
  degraded,

  /// The status endpoint could not be reached or returned something unusable.
  unavailable,
}

/// A ready-to-render banner state: a [level] (which drives colour + whether the
/// dot pulses) and the exact user-facing [text].
@immutable
class StatusSnapshot {
  const StatusSnapshot({
    required this.level,
    required this.text,
    this.model = '',
  });

  final StatusLevel level;
  final String text;
  final String model;

  /// Exact copy is fixed by the product spec and must not drift. This backend
  /// is GPU-only: when the GPUs are offline there is no CPU fallback, so the
  /// copy must not claim the service is still answering "on CPU".
  static const String onlineText = 'Running on 2x GPUs - ONLINE';
  static const String degradedText =
      '2x GPUs offline (repurposed for training) - currently unavailable';
  static const String unavailableText = 'Status unavailable';

  /// Map a raw backend status onto a banner snapshot.
  factory StatusSnapshot.fromStatus(SystemStatus status) {
    return status.gpuOnline
        ? StatusSnapshot(
            level: StatusLevel.online,
            text: onlineText,
            model: status.model,
          )
        : StatusSnapshot(
            level: StatusLevel.degraded,
            text: degradedText,
            model: status.model,
          );
  }

  /// The neutral, non-alarming state shown before the first poll completes and
  /// whenever a poll fails. Polling continues, so this recovers on its own.
  const StatusSnapshot.unavailable()
      : level = StatusLevel.unavailable,
        text = unavailableText,
        model = '';
}

/// Owns the site-wide status poll and exposes the current [StatusSnapshot].
///
/// Starts in the neutral state, fetches immediately on [start], then re-polls
/// every [interval]. A failed fetch is swallowed into the neutral state (the
/// banner never crashes the app), and polling keeps running so the banner
/// recovers when the backend comes back. The timer is cancelled on [dispose] so
/// there is no leak.
///
/// The fetcher is injected so widget/unit tests can drive all three states from
/// a fake and never hit a real backend.
class StatusController extends ChangeNotifier {
  StatusController({
    required StatusFetcher fetcher,
    Duration interval = kStatusPollInterval,
    StatusSnapshot initial = const StatusSnapshot.unavailable(),
  })  : _fetcher = fetcher,
        _interval = interval,
        _snapshot = initial;

  /// Convenience constructor that polls the real `/api/status` endpoint on the
  /// configured backend host. Used by `main.dart`; tests use the primary
  /// constructor with a fake fetcher instead.
  factory StatusController.http({
    required String baseUrl,
    http.Client? client,
    Duration interval = kStatusPollInterval,
  }) {
    final fetcher = HttpStatusFetcher(baseUrl: baseUrl, client: client);
    return StatusController(fetcher: fetcher.call, interval: interval);
  }

  final StatusFetcher _fetcher;
  final Duration _interval;

  StatusSnapshot _snapshot;
  StatusSnapshot get snapshot => _snapshot;

  Timer? _timer;
  bool _disposed = false;

  /// Begin polling: fetch once now, then on a fixed interval.
  void start() {
    refresh();
    _timer?.cancel();
    _timer = Timer.periodic(_interval, (_) => refresh());
  }

  /// Fetch the status once and publish the resulting snapshot. Never throws:
  /// any failure becomes the neutral "unavailable" state.
  Future<void> refresh() async {
    StatusSnapshot next;
    try {
      next = StatusSnapshot.fromStatus(await _fetcher());
    } catch (_) {
      next = const StatusSnapshot.unavailable();
    }
    if (_disposed) return;
    _snapshot = next;
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _timer?.cancel();
    _timer = null;
    super.dispose();
  }
}
