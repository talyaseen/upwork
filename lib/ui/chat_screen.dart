import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../app/theme.dart';
import '../config/app_config.dart';
import '../models/chat_message.dart';
import '../state/chat_controller.dart';
import '../state/status_controller.dart';
import 'widgets/chat_input.dart';
import 'widgets/empty_state.dart';
import 'widgets/message_bubble.dart';
import 'widgets/skill_selector.dart';
import 'widgets/status_banner.dart';

/// The single screen of the app: a branded app bar, the scrolling transcript
/// (or the welcome state), and the composer pinned to the bottom.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final ScrollController _scroll = ScrollController();
  int _lastCount = 0;

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  /// Whether the transcript is currently pinned at (or very near) the bottom.
  /// Used to decide whether a streaming answer should keep the view following
  /// its tail: if the user has deliberately scrolled up to read earlier
  /// messages, the auto-follow must not yank them back down mid-read.
  bool _isNearBottom() {
    if (!_scroll.hasClients) return true;
    final position = _scroll.position;
    return position.maxScrollExtent - position.pixels <= 120;
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<ChatController>();
    final statusController = context.watch<StatusController>();

    // Scroll to bottom when a NEW message arrives (the user just sent one, or
    // the assistant's turn appeared). While an answer streams, only keep
    // following its tail if the user is already at the bottom - otherwise they
    // scrolled up on purpose to read back, and hijacking that is infuriating.
    final bool isStreaming = controller.messages.isNotEmpty &&
        controller.messages.last.status == MessageStatus.streaming;
    final bool countChanged = controller.messages.length != _lastCount;
    if (countChanged) {
      _lastCount = controller.messages.length;
      _scrollToBottom();
    } else if (isStreaming && _isNearBottom()) {
      _scrollToBottom();
    }

    return Scaffold(
      appBar: _buildAppBar(controller),
      body: Column(
        children: [
          StatusBanner(controller: statusController),
          if (controller.session == SessionStatus.failed)
            _SessionBanner(
              message: controller.sessionError ??
                  'Could not connect to the assistant.',
              onRetry: controller.connect,
            ),
          Expanded(
            child: controller.hasMessages
                ? _buildTranscript(controller)
                : EmptyState(
                    // Honour the same gate as the composer: a suggestion chip
                    // must not fire a send while the session is still
                    // connecting or has failed. When disabled the tap is a
                    // no-op so a mid-connect chip press cannot slip a request
                    // through.
                    onSuggestion: _composerEnabled(controller)
                        ? controller.send
                        : (_) {},
                  ),
          ),
          SkillSelector(
            selected: controller.skill,
            onChanged: controller.setSkill,
            enabled: _composerEnabled(controller),
          ),
          ChatInput(
            enabled: _composerEnabled(controller),
            onSend: controller.send,
            hintText: controller.skill.hint,
          ),
        ],
      ),
    );
  }

  /// The composer, skill selector and suggestion chips share one gate: the demo
  /// session is connected and no request is currently in flight.
  bool _composerEnabled(ChatController controller) =>
      controller.session == SessionStatus.ready && !controller.isSending;

  Widget _buildTranscript(ChatController controller) {
    return ListView.builder(
      controller: _scroll,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemCount: controller.messages.length,
      itemBuilder: (context, index) {
        final message = controller.messages[index];
        // Retry only acts on the LAST turn (see ChatController.retryLast), so
        // only the last bubble gets the affordance - otherwise every earlier
        // error bubble shows a "Retry" that would silently act on a different
        // (the latest) message.
        final bool isLast = index == controller.messages.length - 1;
        return Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 820),
            child: MessageBubble(
              message: message,
              onRetry: isLast ? controller.retryLast : null,
            ),
          ),
        );
      },
    );
  }

  PreferredSizeWidget _buildAppBar(ChatController controller) {
    return AppBar(
      title: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              gradient: AppTheme.brandGradient,
              borderRadius: BorderRadius.circular(AppTheme.radiusSm + 2),
              boxShadow: AppTheme.shadowSm,
            ),
            child: const Icon(Icons.auto_awesome, size: 19, color: Colors.black),
          ),
          const SizedBox(width: AppTheme.spaceMd),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(AppConfig.appName, style: AppTheme.title),
              Text(AppConfig.appTagline, style: AppTheme.caption),
            ],
          ),
        ],
      ),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: AppTheme.spaceSm),
          child: _NewChatButton(controller: controller),
        ),
        Padding(
          padding: const EdgeInsets.only(right: AppTheme.spaceLg),
          child: _StatusPill(status: controller.session),
        ),
      ],
    );
  }
}

/// Visible, reachable control that clears the transcript and starts a
/// genuinely fresh conversation (see [ChatController.startNewChat]). Confirms
/// first when there is an active conversation to lose; starts immediately
/// when the transcript is already empty (nothing to confirm).
class _NewChatButton extends StatelessWidget {
  const _NewChatButton({required this.controller});

  final ChatController controller;

  Future<void> _handleTap(BuildContext context) async {
    if (controller.hasMessages) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          backgroundColor: AppTheme.surfaceRaised,
          title: const Text('Start a new chat?'),
          content: const Text(
            'This clears the current conversation and starts a fresh '
            'session.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('New chat'),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
    }
    controller.startNewChat();
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.surfaceRaised,
      borderRadius: BorderRadius.circular(AppTheme.radiusPill),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppTheme.radiusPill),
        onTap: () => _handleTap(context),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppTheme.spaceMd,
            vertical: AppTheme.spaceSm,
          ),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppTheme.radiusPill),
            border: Border.all(color: AppTheme.border),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.add_comment_outlined,
                  size: 15, color: AppTheme.textMuted),
              const SizedBox(width: AppTheme.spaceXs + 2),
              Text(
                'New chat',
                style: AppTheme.caption.copyWith(
                  color: AppTheme.textMuted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status});

  final SessionStatus status;

  @override
  Widget build(BuildContext context) {
    late final Color color;
    late final String label;
    switch (status) {
      case SessionStatus.connecting:
        color = AppTheme.accentAlt;
        label = 'Connecting';
      case SessionStatus.ready:
        color = AppTheme.accent;
        label = 'Connected';
      case SessionStatus.failed:
        color = AppTheme.danger;
        label = 'Offline';
    }
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppTheme.spaceMd - 2,
        vertical: AppTheme.spaceSm - 2,
      ),
      decoration: BoxDecoration(
        color: AppTheme.surfaceRaised,
        borderRadius: BorderRadius.circular(AppTheme.radiusPill),
        border: Border.all(color: AppTheme.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: color.withValues(alpha: 0.7),
                  blurRadius: 5,
                  spreadRadius: 0.5,
                ),
              ],
            ),
          ),
          const SizedBox(width: AppTheme.spaceXs + 3),
          Text(
            label,
            style: AppTheme.caption.copyWith(
              color: AppTheme.textMuted,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _SessionBanner extends StatelessWidget {
  const _SessionBanner({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.danger.withValues(alpha: 0.12),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppTheme.spaceLg - 4,
          vertical: AppTheme.spaceSm + 2,
        ),
        child: Row(
          children: [
            const Icon(Icons.cloud_off, color: AppTheme.danger, size: 18),
            const SizedBox(width: AppTheme.spaceSm + 2),
            Expanded(
              child: Text(message, style: AppTheme.body.copyWith(fontSize: 13)),
            ),
            TextButton(
              onPressed: onRetry,
              child: Text(
                'Reconnect',
                style: AppTheme.bodyStrong.copyWith(
                  color: AppTheme.accent,
                  fontSize: 13,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
