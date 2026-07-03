import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../app/theme.dart';
import '../../models/chat_message.dart';
import '../../models/chat_skill.dart';
import 'artifact_view.dart';
import 'citation_card.dart';
import 'markdown_body.dart';
import 'typing_indicator.dart';

/// Renders a single chat turn: a right-aligned user bubble, or a left-aligned
/// assistant bubble that may show a typing indicator, an error state, or a
/// grounded answer followed by its source citations.
class MessageBubble extends StatelessWidget {
  const MessageBubble({super.key, required this.message, this.onRetry});

  final ChatMessage message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) const _Avatar(),
          if (!isUser) const SizedBox(width: 10),
          Flexible(
            child: Column(
              crossAxisAlignment:
                  isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                _Bubble(message: message, onRetry: onRetry),
                if (!isUser && message.artifacts.isNotEmpty)
                  _Artifacts(message: message),
                if (!isUser && message.citations.isNotEmpty)
                  _Citations(message: message),
              ],
            ),
          ),
          if (isUser) const SizedBox(width: 10),
          if (isUser) const _Avatar(isUser: true),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message, this.onRetry});

  final ChatMessage message;
  final VoidCallback? onRetry;

  bool get _isError => message.status == MessageStatus.error;
  bool get _isBusy => message.status == MessageStatus.busy;
  bool get _isOffline => message.status == MessageStatus.offline;
  bool get _isQueued => message.status == MessageStatus.queued;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    // Error and the two "no real answer" backend states (busy / offline) all
    // render on the muted surface; a normal answer sits on the raised surface.
    final bool onMutedSurface = _isError || _isBusy || _isOffline;

    final Color bg = isUser
        ? AppTheme.userBubble
        : (onMutedSurface ? AppTheme.surface : AppTheme.surfaceRaised);
    final Color borderColor = _isError
        ? AppTheme.danger.withValues(alpha: 0.5)
        : ((_isBusy || _isOffline)
            ? AppTheme.warning.withValues(alpha: 0.5)
            : AppTheme.border);
    final BorderRadius radius = BorderRadius.only(
      topLeft: const Radius.circular(AppTheme.radiusLg),
      topRight: const Radius.circular(AppTheme.radiusLg),
      bottomLeft: Radius.circular(isUser ? AppTheme.radiusLg : 4),
      bottomRight: Radius.circular(isUser ? 4 : AppTheme.radiusLg),
    );

    return Container(
      constraints: const BoxConstraints(maxWidth: 560),
      padding: const EdgeInsets.symmetric(
        horizontal: AppTheme.spaceLg - 4,
        vertical: AppTheme.spaceMd,
      ),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: radius,
        border: Border.all(color: borderColor),
        boxShadow: AppTheme.shadowSm,
      ),
      child: _content(context),
    );
  }

  Widget _content(BuildContext context) {
    if (message.status == MessageStatus.sending ||
        message.status == MessageStatus.queued) {
      // No tokens yet. The first token can take several seconds while the model
      // reads the retrieved context, so show a clear "working" indicator with a
      // label so it never looks frozen. While queued, the label reports the
      // honest waiting-in-line status instead of pretending work has started.
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const TypingIndicator(),
            const SizedBox(width: AppTheme.spaceMd),
            Flexible(
              child: Text(
                _isQueued && (message.notice?.isNotEmpty ?? false)
                    ? message.notice!
                    : 'Retrieving sources and thinking...',
                style: AppTheme.caption,
              ),
            ),
          ],
        ),
      );
    }

    if (_isError) {
      return _noticeRow(
        icon: Icons.error_outline,
        iconColor: AppTheme.danger,
        text: message.text,
        showRetry: true,
      );
    }

    if (_isBusy) {
      // Server at capacity: no generation ran. Honest, distinct from an
      // ungrounded answer, and retryable.
      return _noticeRow(
        icon: Icons.hourglass_empty,
        iconColor: AppTheme.warning,
        text: message.notice ??
            'The demo is at capacity right now. Please try again in a few '
                'seconds.',
        showRetry: true,
      );
    }

    if (_isOffline) {
      // Demo paused (GPU yielded to training). If any answer text had already
      // streamed, keep it and flag the truncation; otherwise show just the
      // notice. Either way it is NOT a completed answer.
      final hasPartial = message.text.trim().isNotEmpty;
      return Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.cloud_off, color: AppTheme.warning, size: 18),
          const SizedBox(width: AppTheme.spaceSm),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (hasPartial) ...[
                  SelectableText(message.text, style: AppTheme.body),
                  const SizedBox(height: AppTheme.spaceSm),
                ],
                Text(
                  message.notice ??
                      'The live demo is paused right now (the GPU is '
                          'training). Please try again shortly.',
                  style: AppTheme.caption,
                ),
                if (hasPartial)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      'The answer above was cut off.',
                      style: AppTheme.caption
                          .copyWith(color: AppTheme.textFaint),
                    ),
                  ),
                if (onRetry != null) _retryLink(),
              ],
            ),
          ),
        ],
      );
    }

    final routedSkill = message.isUser ? null : message.routedSkill;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (routedSkill != null || (!message.isUser && !message.grounded))
          Padding(
            padding: const EdgeInsets.only(bottom: AppTheme.spaceSm - 2),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Which skill the backend ACTUALLY routed this turn to. Shown
                // per-message so it is unambiguous even when it differs from the
                // mode the user had selected (the backend auto-routes).
                if (routedSkill != null) _SkillBadge(skill: routedSkill),
                if (routedSkill != null && !message.grounded)
                  const SizedBox(width: AppTheme.spaceSm - 2),
                if (!message.grounded) ...[
                  const Icon(Icons.info_outline,
                      size: 15, color: AppTheme.textMuted),
                  const SizedBox(width: AppTheme.spaceSm - 2),
                  Text(
                    'No grounded source',
                    style: AppTheme.label.copyWith(fontSize: 11.5),
                  ),
                ],
              ],
            ),
          ),
        _answerText(),
      ],
    );
  }

  /// A single-icon informational row (error / busy) with an optional Retry.
  Widget _noticeRow({
    required IconData icon,
    required Color iconColor,
    required String text,
    required bool showRetry,
  }) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: iconColor, size: 18),
        const SizedBox(width: AppTheme.spaceSm),
        Flexible(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(text, style: AppTheme.body),
              if (showRetry && onRetry != null) _retryLink(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _retryLink() {
    return Padding(
      padding: const EdgeInsets.only(top: AppTheme.spaceXs + 2),
      child: GestureDetector(
        onTap: onRetry,
        child: Text(
          'Retry',
          style: AppTheme.bodyStrong.copyWith(
            color: AppTheme.accent,
            fontSize: 13,
          ),
        ),
      ),
    );
  }

  Widget _answerText() {
    final style = AppTheme.body.copyWith(
      color: message.isUser ? Colors.white : AppTheme.textPrimary,
    );
    if (message.isUser) {
      // The user's own turn is never streamed - render it immediately.
      return SelectableText(message.text, style: style);
    }
    if (message.status == MessageStatus.streaming) {
      // While tokens are still arriving, pace the reveal character-by-character
      // (with a brief catch-up if the network outruns the reveal) so the text
      // reads like a natural typewriter instead of snapping into view in rigid,
      // SSE-chunk-sized blocks. Partial Markdown (a half-streamed table row or
      // an unclosed code fence) can't render meaningfully yet, so the raw text
      // is shown live and re-rendered as real Markdown the moment it completes.
      return _PacedText(
        text: message.text,
        isStreaming: true,
        style: style,
      );
    }
    // Finished answer (complete / noAnswer / grounded-hint): render the body as
    // Markdown - headings, GFM tables (the code-review Findings table), fenced
    // code blocks and inline emphasis - so it reads as formatted output instead
    // of literal `##`, `| ... |` and ``` ` ``` source, matching the artifact
    // card's renderer exactly. When the same message already shows a Mermaid
    // diagram as a card below, the duplicative raw ```mermaid source is stripped
    // from the prose so the diagram source is not shown twice.
    final hasDiagram = message.artifacts.any((a) => a.isDiagram);
    final body =
        hasDiagram ? stripMermaidFences(message.text) : message.text;
    return MarkdownBody(
      markdown: body,
      boxed: false,
      // Keep normal answer prose at the chat's conversational body size.
      paragraphSize: AppTheme.body.fontSize!,
    );
  }
}

/// A small, tasteful pill badge naming the skill the backend actually routed
/// an assistant turn to ("Q&A" / "Code review" / "Diagram"). It uses the same
/// accent tokens as the rest of the product so it reads as a native label, and
/// it is the per-message source of truth for which skill handled the message -
/// unambiguous even when the backend's auto-routing differs from the mode the
/// user had selected in the composer's skill selector.
class _SkillBadge extends StatelessWidget {
  const _SkillBadge({required this.skill});

  final ChatSkill skill;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppTheme.spaceSm, vertical: 3),
      decoration: BoxDecoration(
        color: AppTheme.accentDim,
        borderRadius: BorderRadius.circular(AppTheme.radiusSm - 2),
        border: Border.all(color: AppTheme.accent.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(skill.icon, size: 12, color: AppTheme.accent),
          const SizedBox(width: AppTheme.spaceXs + 1),
          Text(
            skill.badgeLabel,
            style: AppTheme.label.copyWith(
              fontSize: 10.5,
              letterSpacing: 0.4,
              color: AppTheme.accent,
            ),
          ),
        ],
      ),
    );
  }
}

/// A thin blinking caret shown at the end of an answer while it is streaming.
class _StreamingCaret extends StatefulWidget {
  const _StreamingCaret();

  @override
  State<_StreamingCaret> createState() => _StreamingCaretState();
}

class _StreamingCaretState extends State<_StreamingCaret>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 2),
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          return Opacity(
            opacity: _controller.value < 0.5 ? 1.0 : 0.15,
            child: Container(
              width: 7,
              height: 15,
              decoration: BoxDecoration(
                color: AppTheme.accent,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// Paces the reveal of an assistant answer to a smooth, readable
/// character-by-character cadence instead of snapping each SSE chunk into
/// view the instant it lands. A single per-message [Ticker] advances a
/// "visible" character count towards the "target" [text] (the full text
/// received so far) at a natural reading pace, speeding up to catch up
/// whenever the target gets far ahead - a big chunk just arrived, or the
/// stream has already finished - so a long answer never trickles for ages.
/// Only one ticker runs per active streaming message, and it stops itself the
/// moment the visible text catches up to the target (including after the
/// network stream itself has finished), so there is never a wasted animation
/// frame once the answer is fully revealed.
class _PacedText extends StatefulWidget {
  const _PacedText({
    required this.text,
    required this.isStreaming,
    required this.style,
  });

  /// The full text received from the backend so far (or the whole answer,
  /// once the stream is done). Grows monotonically as tokens arrive.
  final String text;

  /// Whether the backend stream for this message is still in flight.
  final bool isStreaming;

  final TextStyle style;

  @override
  State<_PacedText> createState() => _PacedTextState();
}

class _PacedTextState extends State<_PacedText>
    with SingleTickerProviderStateMixin {
  // Natural reading pace: quicker than literal human typing (this is a
  // reveal, not real typing) but slow enough to read as deliberate rather
  // than an instant AI text-dump. ~26ms per character.
  static const double _baseCharsPerSecond = 38;

  // Once the reveal falls this far behind the text actually received, speed
  // up so it catches up in well under a second instead of trickling forever;
  // below the cap it settles back to the natural pace above.
  static const int _backlogCapChars = 50;
  static const double _catchUpSeconds = 0.6;

  // Created eagerly in initState (NOT via a lazy `late final = createTicker(...)`
  // field initializer): _maybeStart() below can return before ever touching
  // _ticker (e.g. a message that arrives already-complete, common with a fast
  // or fully-synchronous backend), which would otherwise defer the ticker's
  // creation to whenever it is first referenced - including dispose(), where
  // SingleTickerProviderStateMixin.createTicker's ancestor (TickerMode) lookup
  // throws because the element tree is no longer stable at that point.
  late final Ticker _ticker;
  Duration _lastElapsed = Duration.zero;
  double _carry = 0;
  int _visible = 0;

  @override
  void initState() {
    super.initState();
    _ticker = createTicker(_onTick);
    // A message only reaches this widget once it has left the `sending`
    // state (see _Bubble._content). If it is not currently streaming it is
    // already-complete (e.g. rebuilt after citations/artifacts changed) -
    // show it in full rather than replaying the typewriter effect.
    _visible = widget.isStreaming ? 0 : widget.text.length;
    _maybeStart();
  }

  @override
  void didUpdateWidget(covariant _PacedText oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.text != widget.text ||
        oldWidget.isStreaming != widget.isStreaming) {
      if (_visible > widget.text.length) _visible = widget.text.length;
      _maybeStart();
    }
  }

  void _maybeStart() {
    if (_visible >= widget.text.length) return;
    if (!_ticker.isActive) {
      _lastElapsed = Duration.zero;
      _carry = 0;
      _ticker.start();
    }
  }

  void _onTick(Duration elapsed) {
    final target = widget.text.length;
    final backlog = target - _visible;
    if (backlog <= 0) {
      _ticker.stop();
      return;
    }
    final deltaSeconds = (elapsed - _lastElapsed).inMicroseconds /
        Duration.microsecondsPerSecond;
    _lastElapsed = elapsed;
    final rate = backlog > _backlogCapChars
        ? backlog / _catchUpSeconds
        : _baseCharsPerSecond;
    _carry += rate * deltaSeconds;
    final step = _carry.floor();
    if (step <= 0) return;
    _carry -= step;
    setState(() {
      _visible += step;
      if (_visible > target) _visible = target;
    });
    if (_visible >= target) {
      _ticker.stop();
    }
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }

  /// Never cut between the two UTF-16 code units of a surrogate pair (an emoji
  /// or other astral-plane glyph): a reveal boundary that lands there would
  /// otherwise briefly render a broken replacement character until the next
  /// tick completes the pair. If [end] sits just after a high surrogate, step
  /// it back one so the pair is revealed whole on the following tick.
  static int _safeBoundary(String text, int end) {
    if (end <= 0 || end >= text.length) return end;
    final unit = text.codeUnitAt(end - 1);
    final isHighSurrogate = unit >= 0xD800 && unit <= 0xDBFF;
    return isHighSurrogate ? end - 1 : end;
  }

  @override
  Widget build(BuildContext context) {
    final shown = widget.text.substring(0, _safeBoundary(widget.text, _visible));
    final stillRevealing = widget.isStreaming || _visible < widget.text.length;
    if (!stillRevealing) {
      return SelectableText(shown, style: widget.style);
    }
    return SelectableText.rich(
      TextSpan(
        text: shown,
        style: widget.style,
        children: const [
          WidgetSpan(
            alignment: PlaceholderAlignment.middle,
            child: _StreamingCaret(),
          ),
        ],
      ),
    );
  }
}

class _Artifacts extends StatelessWidget {
  const _Artifacts({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      // Wider than the text bubble so diagrams and reviews have room to breathe.
      constraints: const BoxConstraints(maxWidth: 720),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final artifact in message.artifacts)
            ArtifactView(artifact: artifact),
        ],
      ),
    );
  }
}

class _Citations extends StatelessWidget {
  const _Citations({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 560),
      margin: const EdgeInsets.only(top: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 2, bottom: 2, top: 2),
            child: Text('SOURCES', style: AppTheme.label.copyWith(fontSize: 10.5)),
          ),
          for (var i = 0; i < message.citations.length; i++)
            CitationCard(citation: message.citations[i], index: i + 1),
        ],
      ),
    );
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({this.isUser = false});

  final bool isUser;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        color: isUser ? AppTheme.userBubble : null,
        gradient: isUser ? null : AppTheme.brandGradient,
        borderRadius: BorderRadius.circular(AppTheme.radiusSm + 1),
        border: isUser ? Border.all(color: AppTheme.border) : null,
        boxShadow: AppTheme.shadowSm,
      ),
      child: Icon(
        isUser ? Icons.person_outline : Icons.auto_awesome,
        size: 17,
        color: isUser ? Colors.white : Colors.black,
      ),
    );
  }
}
