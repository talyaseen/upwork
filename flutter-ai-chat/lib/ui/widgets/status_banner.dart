import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../state/status_controller.dart';

/// Stable keys so tests can locate the dot and assert its colour per state.
const Key kStatusBannerKey = Key('status-banner');
const Key kStatusBannerDotKey = Key('status-banner-dot');

/// Site-wide top status banner.
///
/// Renders the current [StatusController.snapshot] as a slim strip with a
/// status dot and a short label. The dot pulses while the status endpoint is
/// reachable (green when the GPUs are serving, amber when they are offline and
/// the service is unavailable) and sits static and grey when the status
/// endpoint itself cannot be reached. The controller owns the poll loop
/// and lifecycle; this widget only animates and draws, and is rebuilt by the
/// controller's [ChangeNotifier] notifications.
class StatusBanner extends StatelessWidget {
  const StatusBanner({super.key, required this.controller});

  final StatusController controller;

  Color _colorFor(StatusLevel level) {
    switch (level) {
      case StatusLevel.online:
        return AppTheme.accent;
      case StatusLevel.degraded:
        return AppTheme.warning;
      case StatusLevel.unavailable:
        return AppTheme.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        final snapshot = controller.snapshot;
        final color = _colorFor(snapshot.level);
        final pulse = snapshot.level != StatusLevel.unavailable;
        return Material(
          key: kStatusBannerKey,
          color: AppTheme.surface,
          child: Container(
            width: double.infinity,
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppTheme.border)),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _PulsingDot(color: color, pulse: pulse),
                const SizedBox(width: 9),
                Flexible(
                  child: Text(
                    snapshot.text,
                    textAlign: TextAlign.center,
                    style: AppTheme.caption.copyWith(
                      color: snapshot.level == StatusLevel.unavailable
                          ? AppTheme.textMuted
                          : AppTheme.textPrimary,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// A small status dot. The base [Container] keeps a fixed [color] (so tests can
/// read it deterministically); the pulse is a scale + opacity animation layered
/// on top, and is disabled when [pulse] is false (neutral state).
class _PulsingDot extends StatefulWidget {
  const _PulsingDot({required this.color, required this.pulse});

  final Color color;
  final bool pulse;

  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    // Created eagerly (not lazily) so dispose() never has to initialise a
    // ticker on a deactivated element.
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    );
    if (widget.pulse) _ctrl.repeat(reverse: true);
  }

  @override
  void didUpdateWidget(covariant _PulsingDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.pulse && !_ctrl.isAnimating) {
      _ctrl.repeat(reverse: true);
    } else if (!widget.pulse && _ctrl.isAnimating) {
      _ctrl.stop();
      _ctrl.value = 0;
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Widget _dot() => Container(
        key: kStatusBannerDotKey,
        width: 9,
        height: 9,
        decoration: BoxDecoration(
          color: widget.color,
          shape: BoxShape.circle,
        ),
      );

  @override
  Widget build(BuildContext context) {
    if (!widget.pulse) return _dot();
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (context, child) {
        final t = _ctrl.value; // 0..1, reversing
        return Opacity(
          opacity: 0.45 + 0.55 * t,
          child: Transform.scale(scale: 0.85 + 0.30 * t, child: child),
        );
      },
      child: _dot(),
    );
  }
}
