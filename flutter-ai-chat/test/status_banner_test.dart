import 'dart:async';

import 'package:fake_async/fake_async.dart';
import 'package:flutter/material.dart';
import 'package:flutter_ai_chat/app/theme.dart';
import 'package:flutter_ai_chat/models/system_status.dart';
import 'package:flutter_ai_chat/state/status_controller.dart';
import 'package:flutter_ai_chat/ui/widgets/status_banner.dart';
import 'package:flutter_test/flutter_test.dart';

// All tests here drive the banner through a fake fetcher and never touch a real
// backend or the network. They cover the three required states (green / amber /
// neutral), the exact text per state, and that a failed fetch degrades to the
// neutral state without throwing.

SystemStatus _online() => const SystemStatus(
      tier: 'gpu',
      gpuOnline: true,
      model: 'qwen2.5:7b-instruct',
    );

// GPU-only backend: when the GPUs are offline the tier is 'offline' and no
// answers are served (there is no CPU fallback).
SystemStatus _offline() => const SystemStatus(
      tier: 'offline',
      gpuOnline: false,
      model: 'qwen2.5:7b-instruct',
    );

Color _dotColor(WidgetTester tester) {
  final container = tester.widget<Container>(find.byKey(kStatusBannerDotKey));
  return (container.decoration as BoxDecoration).color!;
}

Future<void> _pumpBanner(WidgetTester tester, StatusController controller,
    {bool pulsing = true}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: StatusBanner(controller: controller)),
    ),
  );
  // A pulsing dot animates forever, so settle with a bounded pump; the neutral
  // state has no animation and can settle normally.
  if (pulsing) {
    await tester.pump(const Duration(milliseconds: 50));
  } else {
    await tester.pumpAndSettle();
  }
}

void main() {
  group('StatusController.refresh maps the backend status', () {
    test('gpu_online == true -> online state with exact online text', () async {
      final c = StatusController(fetcher: () async => _online());
      addTearDown(c.dispose);

      await c.refresh();

      expect(c.snapshot.level, StatusLevel.online);
      expect(c.snapshot.text, 'Running on 2x GPUs - ONLINE');
      expect(c.snapshot.text, StatusSnapshot.onlineText);
    });

    test(
        'gpu_online == false -> degraded state with GPU-only "unavailable" '
        'copy (no false "running on CPU" claim)', () async {
      final c = StatusController(fetcher: () async => _offline());
      addTearDown(c.dispose);

      await c.refresh();

      expect(c.snapshot.level, StatusLevel.degraded);
      expect(
        c.snapshot.text,
        '2x GPUs offline (repurposed for training) - currently unavailable',
      );
      expect(c.snapshot.text, StatusSnapshot.degradedText);
      // GPU-only reality: the copy must never claim CPU serving/answers.
      expect(c.snapshot.text.toLowerCase(), isNot(contains('cpu')));
    });

    test('a failed fetch degrades to neutral without throwing', () async {
      final c = StatusController(
        fetcher: () async => throw TimeoutException('unreachable'),
      );
      addTearDown(c.dispose);

      // Must not throw.
      await c.refresh();

      expect(c.snapshot.level, StatusLevel.unavailable);
      expect(c.snapshot.text, 'Status unavailable');
    });

    test('recovers from neutral back to online on a later successful poll',
        () async {
      var fail = true;
      final c = StatusController(fetcher: () async {
        if (fail) throw const SocketishError();
        return _online();
      });
      addTearDown(c.dispose);

      await c.refresh();
      expect(c.snapshot.level, StatusLevel.unavailable);

      fail = false;
      await c.refresh();
      expect(c.snapshot.level, StatusLevel.online);
    });
  });

  group('StatusController polling lifecycle', () {
    test('start() fetches immediately then on the interval; dispose cancels',
        () {
      fakeAsync((async) {
        var calls = 0;
        final c = StatusController(
          fetcher: () async {
            calls++;
            return _online();
          },
          interval: const Duration(seconds: 15),
        );

        c.start();
        async.flushMicrotasks();
        expect(calls, 1, reason: 'an immediate fetch on start');

        async.elapse(const Duration(seconds: 15));
        expect(calls, 2, reason: 'one poll after the interval');

        async.elapse(const Duration(seconds: 15));
        expect(calls, 3);

        c.dispose();
        async.elapse(const Duration(seconds: 60));
        expect(calls, 3, reason: 'no further polls after dispose');
      });
    });
  });

  group('StatusBanner rendering', () {
    testWidgets('online -> green dot + exact online text', (tester) async {
      final c = StatusController(
        fetcher: () async => _online(),
        initial: StatusSnapshot.fromStatus(_online()),
      );
      addTearDown(c.dispose);
      await _pumpBanner(tester, c);

      expect(find.text('Running on 2x GPUs - ONLINE'), findsOneWidget);
      expect(_dotColor(tester), AppTheme.accent);
    });

    testWidgets('degraded -> amber dot + GPU-only "unavailable" text',
        (tester) async {
      final c = StatusController(
        fetcher: () async => _offline(),
        initial: StatusSnapshot.fromStatus(_offline()),
      );
      addTearDown(c.dispose);
      await _pumpBanner(tester, c);

      expect(
        find.text(
          '2x GPUs offline (repurposed for training) - currently unavailable',
        ),
        findsOneWidget,
      );
      expect(_dotColor(tester), AppTheme.warning);
    });

    testWidgets('unavailable -> grey dot + neutral text', (tester) async {
      final c = StatusController(
        fetcher: () async => throw Exception('x'),
        // default initial is the neutral/unavailable state
      );
      addTearDown(c.dispose);
      await _pumpBanner(tester, c, pulsing: false);

      expect(find.text('Status unavailable'), findsOneWidget);
      expect(_dotColor(tester), AppTheme.textMuted);
    });
  });
}

/// A trivial throwing error used to simulate an unreachable endpoint without
/// importing dart:io (which is unavailable on the web target).
class SocketishError implements Exception {
  const SocketishError();
}
