import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../models/citation.dart';

/// An expandable source card shown beneath a grounded answer.
///
/// Collapsed it shows the source title and a relevance badge; expanded it
/// reveals the exact passage the answer was drawn from. This is what makes the
/// assistant read as trustworthy: the user can verify every claim.
class CitationCard extends StatefulWidget {
  const CitationCard({super.key, required this.citation, required this.index});

  final Citation citation;
  final int index;

  @override
  State<CitationCard> createState() => _CitationCardState();
}

class _CitationCardState extends State<CitationCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final c = widget.citation;
    return Container(
      margin: const EdgeInsets.only(top: AppTheme.spaceSm),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        border: Border.all(
          color: _expanded ? AppTheme.accent.withValues(alpha: 0.35) : AppTheme.border,
        ),
        boxShadow: _expanded ? AppTheme.shadowSm : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(AppTheme.radiusMd),
          onTap: () => setState(() => _expanded = !_expanded),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppTheme.spaceMd,
              vertical: AppTheme.spaceSm + 2,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 22,
                      height: 22,
                      alignment: Alignment.center,
                      decoration: const BoxDecoration(
                        color: AppTheme.accentDim,
                        shape: BoxShape.circle,
                      ),
                      child: Text(
                        '${widget.index}',
                        style: const TextStyle(
                          fontFamily: AppTheme.monoFontFamily,
                          color: AppTheme.accentBright,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: AppTheme.spaceSm + 2),
                    Expanded(
                      child: Text(
                        c.documentTitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppTheme.bodyStrong.copyWith(fontSize: 13),
                      ),
                    ),
                    const SizedBox(width: AppTheme.spaceSm),
                    _RelevanceBadge(percent: c.relevancePercent),
                    const SizedBox(width: AppTheme.spaceXs),
                    Icon(
                      _expanded ? Icons.expand_less : Icons.expand_more,
                      size: 18,
                      color: AppTheme.textMuted,
                    ),
                  ],
                ),
                AnimatedCrossFade(
                  duration: const Duration(milliseconds: 160),
                  crossFadeState: _expanded
                      ? CrossFadeState.showSecond
                      : CrossFadeState.showFirst,
                  firstChild: const SizedBox(width: double.infinity),
                  secondChild: Padding(
                    padding: const EdgeInsets.only(top: AppTheme.spaceSm),
                    child: Text(
                      c.text,
                      style: AppTheme.caption.copyWith(fontSize: 12.5, height: 1.45),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RelevanceBadge extends StatelessWidget {
  const _RelevanceBadge({required this.percent});

  final int percent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: AppTheme.surfaceRaised,
        borderRadius: BorderRadius.circular(AppTheme.radiusPill),
        border: Border.all(color: AppTheme.border),
      ),
      child: Text(
        '$percent% match',
        style: AppTheme.caption.copyWith(fontSize: 10.5, fontWeight: FontWeight.w600),
      ),
    );
  }
}
