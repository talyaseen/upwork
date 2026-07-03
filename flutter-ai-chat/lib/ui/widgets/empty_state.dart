import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// The first-run welcome shown before any messages, with a few suggestion
/// chips that pre-fill realistic questions the seed corpus can answer well.
///
/// The entire panel fades in over 500 ms on first render for a polished entry
/// feel. The animation plays once (non-repeating) so widget tests that call
/// pumpAndSettle() settle cleanly after it completes.
class EmptyState extends StatefulWidget {
  const EmptyState({super.key, required this.onSuggestion});

  final ValueChanged<String> onSuggestion;

  @override
  State<EmptyState> createState() => _EmptyStateState();
}

class _EmptyStateState extends State<EmptyState>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 500),
  )..forward(); // plays once; settles at 1.0 so pumpAndSettle() works fine

  late final Animation<double> _opacity =
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOut);

  static const List<String> _suggestions = [
    'How do stateless services scale?',
    'Where should configuration be stored?',
    'What belongs in a readiness probe?',
    'How should secrets be managed?',
  ];

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: SingleChildScrollView(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      gradient: AppTheme.brandGradient,
                      borderRadius: BorderRadius.circular(AppTheme.radiusXl),
                      boxShadow: AppTheme.shadowMd,
                    ),
                    child: const Icon(
                      Icons.auto_awesome,
                      color: Colors.black,
                      size: 30,
                    ),
                  ),
                  const SizedBox(height: AppTheme.spaceLg),
                  const Text(
                    'Ask me anything, grounded in real sources',
                    textAlign: TextAlign.center,
                    style: AppTheme.headline,
                  ),
                  const SizedBox(height: AppTheme.spaceSm + 2),
                  Text(
                    'Every answer is drawn from an indexed knowledge base and '
                    'comes with the exact sources it used, so you can verify it.',
                    textAlign: TextAlign.center,
                    style: AppTheme.body.copyWith(
                      color: AppTheme.textMuted,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: AppTheme.spaceXl - 4),
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      for (final s in _suggestions)
                        _SuggestionChip(
                          label: s,
                          onTap: () => widget.onSuggestion(s),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SuggestionChip extends StatelessWidget {
  const _SuggestionChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.surfaceRaised,
      borderRadius: BorderRadius.circular(AppTheme.radiusMd),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppTheme.spaceMd + 2,
            vertical: AppTheme.spaceSm + 2,
          ),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppTheme.radiusMd),
            border: Border.all(color: AppTheme.border),
            boxShadow: AppTheme.shadowSm,
          ),
          child: Text(
            label,
            style: AppTheme.bodyStrong.copyWith(fontSize: 13, fontWeight: FontWeight.w500),
          ),
        ),
      ),
    );
  }
}
