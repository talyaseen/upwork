import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../models/chat_skill.dart';

/// Stable key so tests can locate the selector without depending on layout.
const Key kSkillSelectorKey = Key('skill-selector');

/// Opacity applied to a chip when the selector is disabled (e.g. while the
/// client is connecting or a send is in flight). Dimming the whole row is the
/// visual cue that the chips are not tappable right now - the `onTap` was
/// already gated, but without this there was no way for a user to *see* that.
const double kDisabledSkillChipOpacity = 0.4;

/// Always-visible row of mode chips that lets the user explicitly pick which
/// backend skill answers the NEXT message: "Ask a question" (qa, default),
/// "Review my code" (code-review) or "Generate a diagram" (mermaid).
///
/// Before this widget existed there was no client-facing way to reach
/// `code-review` or `mermaid` at all - the backend's `skill` request field
/// (see `app/schemas/chat.py`) was never sent by the client, so those two
/// skills were effectively undiscoverable. Selecting a chip here sets
/// [ChatController.skill], which is sent verbatim as `skill` on every `/chat`
/// call (see `ChatController.send`), so the right skill fires reliably
/// regardless of how the message is worded.
///
/// Rendered above the composer on every screen state (welcome AND active
/// transcript), not just the empty/welcome screen, so it stays discoverable
/// throughout the conversation. The selected chip uses a solid brand-gradient
/// fill (the same signature gradient as the header mark, avatar and send
/// button) with a lifted shadow, so the active mode reads with real
/// confidence rather than a faint tint - a deliberate, native-feeling control
/// rather than a bolted-on afterthought.
class SkillSelector extends StatelessWidget {
  const SkillSelector({
    super.key,
    required this.selected,
    required this.onChanged,
    required this.enabled,
  });

  final ChatSkill selected;
  final ValueChanged<ChatSkill> onChanged;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: kSkillSelectorKey,
      width: double.infinity,
      decoration: const BoxDecoration(
        color: AppTheme.surface,
        border: Border(top: BorderSide(color: AppTheme.border)),
      ),
      padding: const EdgeInsets.fromLTRB(16, AppTheme.spaceMd - 2, 16, 0),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (final skill in ChatSkill.values)
              Padding(
                padding: const EdgeInsets.only(right: AppTheme.spaceSm),
                child: _SkillChip(
                  skill: skill,
                  isSelected: skill == selected,
                  enabled: enabled,
                  onTap: () => onChanged(skill),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SkillChip extends StatelessWidget {
  const _SkillChip({
    required this.skill,
    required this.isSelected,
    required this.enabled,
    required this.onTap,
  });

  final ChatSkill skill;
  final bool isSelected;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color foreground = isSelected ? Colors.black : AppTheme.textMuted;
    final Color border = isSelected ? Colors.transparent : AppTheme.border;

    return AnimatedOpacity(
      duration: const Duration(milliseconds: 150),
      opacity: enabled ? 1.0 : kDisabledSkillChipOpacity,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        decoration: BoxDecoration(
          gradient: isSelected ? AppTheme.brandGradient : null,
          color: isSelected ? null : AppTheme.surfaceRaised,
          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
          boxShadow: isSelected ? AppTheme.shadowLifted : null,
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
          child: InkWell(
            borderRadius: BorderRadius.circular(AppTheme.radiusPill),
            onTap: enabled ? onTap : null,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppTheme.spaceMd + 2,
                vertical: AppTheme.spaceSm + 1,
              ),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                border: Border.all(color: border),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(skill.icon, size: 15, color: foreground),
                  const SizedBox(width: AppTheme.spaceXs + 3),
                  Text(
                    skill.label,
                    style: TextStyle(
                      fontFamily: AppTheme.fontFamily,
                      color: foreground,
                      fontSize: 12.5,
                      fontWeight:
                          isSelected ? FontWeight.w700 : FontWeight.w500,
                    ),
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
