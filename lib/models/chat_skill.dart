import 'package:flutter/material.dart';

/// The curated, public-safe skills the backend exposes (see
/// `app/services/skills.py` and `GET /skills` on the FastAPI service).
///
/// The backend already accepts an explicit `skill` id on `POST /chat`
/// (`app/schemas/chat.py::ChatRequest.skill`) and falls back to `qa` when it
/// is omitted or unknown (`SkillRegistry.resolve`). Before this enum existed,
/// nothing in the client ever sent that field, so the only way to reach
/// `code-review` or `mermaid` was to guess phrasing the (non-existent)
/// auto-detection might respond to - it never actually existed server-side.
/// [ChatSkill] gives the UI a typed, explicit choice that is sent verbatim as
/// `skill` on every request (see [ChatController] and [FastApiBackend.chat]).
enum ChatSkill {
  qa(
    id: 'qa',
    label: 'Ask a question',
    shortLabel: 'Ask',
    badgeLabel: 'Q&A',
    hint: 'Ask about architecture, AI or DevOps...',
    icon: Icons.chat_bubble_outline,
  ),
  codeReview(
    id: 'code-review',
    label: 'Review my code',
    shortLabel: 'Review code',
    badgeLabel: 'Code review',
    hint: 'Paste code, a Dockerfile or CI config to review...',
    icon: Icons.fact_check_outlined,
  ),
  mermaid(
    id: 'mermaid',
    label: 'Generate a diagram',
    shortLabel: 'Diagram',
    badgeLabel: 'Diagram',
    hint: 'Describe what you want diagrammed...',
    icon: Icons.account_tree_outlined,
  );

  const ChatSkill({
    required this.id,
    required this.label,
    required this.shortLabel,
    required this.badgeLabel,
    required this.hint,
    required this.icon,
  });

  /// The exact id the backend expects on `ChatRequest.skill`.
  final String id;

  /// Full label shown in the mode selector.
  final String label;

  /// Compact label, reserved for tighter layouts.
  final String shortLabel;

  /// Short label for the "which skill actually ran" badge shown on each
  /// assistant reply (see `MessageBubble`). Distinct from [label] (an
  /// imperative call-to-action for the selector) and [shortLabel]: this reads
  /// as a noun describing the handled turn - "Q&A" / "Code review" / "Diagram".
  final String badgeLabel;

  /// Composer placeholder text while this skill is active.
  final String hint;

  final IconData icon;

  /// Resolve a wire skill id (as reported by the backend on the metadata event,
  /// or accepted on a request) back to its [ChatSkill]. Returns null for a null,
  /// empty or unrecognised id, so callers can treat "no known routed skill" as a
  /// distinct, non-badged case rather than silently defaulting to Q&A.
  static ChatSkill? fromId(String? id) {
    if (id == null || id.isEmpty) return null;
    for (final skill in ChatSkill.values) {
      if (skill.id == id) return skill;
    }
    return null;
  }
}
