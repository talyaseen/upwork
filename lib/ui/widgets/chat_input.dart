import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../app/theme.dart';

/// The message composer: a multi-line text field and a send button, with
/// Enter-to-send (Shift+Enter for a newline) and a disabled state while a
/// request is in flight.
class ChatInput extends StatefulWidget {
  const ChatInput({
    super.key,
    required this.enabled,
    required this.onSend,
    this.hintText = 'Ask about architecture, AI or DevOps...',
  });

  final bool enabled;
  final ValueChanged<String> onSend;

  /// Placeholder shown while [enabled], e.g. swapped by the active skill
  /// (see `ChatSkill`) so the composer hints at what to paste or describe.
  final String hintText;

  /// Hard cap on a single message. Mirrors the backend's `ChatRequest.message`
  /// max_length (4000): sending more is rejected with an opaque HTTP 422, and
  /// the code-review skill actively invites pasting a whole file, so the limit
  /// is enforced in the composer with a visible, friendly counter instead.
  static const int maxLength = 4000;

  @override
  State<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends State<ChatInput> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _canSend = false;
  bool _hasFocus = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      final canSend = _controller.text.trim().isNotEmpty;
      if (canSend != _canSend) setState(() => _canSend = canSend);
    });
    // Drives the composer's focus ring (see build()) - a small but real
    // "this was designed" signal most default Flutter text fields skip.
    _focusNode.addListener(() {
      if (_focusNode.hasFocus != _hasFocus) {
        setState(() => _hasFocus = _focusNode.hasFocus);
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _submit() {
    if (!widget.enabled || !_canSend) return;
    final text = _controller.text;
    _controller.clear();
    widget.onSend(text);
    _focusNode.requestFocus();
  }

  KeyEventResult _onKey(FocusNode node, KeyEvent event) {
    // Both the main-row Enter and the numeric-keypad Enter submit; Shift+Enter
    // (either key) still inserts a newline.
    final isEnter = event.logicalKey == LogicalKeyboardKey.enter ||
        event.logicalKey == LogicalKeyboardKey.numpadEnter;
    if (event is KeyDownEvent &&
        isEnter &&
        !HardwareKeyboard.instance.isShiftPressed) {
      _submit();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  /// Show the character counter only as the message approaches the cap, so the
  /// composer stays clean for ordinary short questions but gives a clear,
  /// friendly heads-up before a long paste is truncated.
  Widget? _buildCounter(
    BuildContext context, {
    required int currentLength,
    required int? maxLength,
    required bool isFocused,
  }) {
    if (maxLength == null || currentLength < maxLength - 500) return null;
    final atLimit = currentLength >= maxLength;
    return Padding(
      padding: const EdgeInsets.only(top: 4, right: 2),
      child: Text(
        atLimit
            ? 'Message limit reached ($maxLength characters)'
            : '$currentLength / $maxLength',
        style: AppTheme.caption.copyWith(
          color: atLimit ? AppTheme.warning : AppTheme.textMuted,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final active = widget.enabled && _canSend;
    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.surface,
        border: Border(top: BorderSide(color: AppTheme.border)),
      ),
      padding: const EdgeInsets.fromLTRB(16, AppTheme.spaceMd, 16, 16),
      child: SafeArea(
        top: false,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                decoration: BoxDecoration(
                  color: AppTheme.background,
                  borderRadius: BorderRadius.circular(AppTheme.radiusMd + 2),
                  border: Border.all(
                    color: _hasFocus ? AppTheme.accent : AppTheme.border,
                  ),
                  boxShadow: _hasFocus
                      ? [
                          BoxShadow(
                            color: AppTheme.accent.withValues(alpha: 0.18),
                            blurRadius: 0,
                            spreadRadius: 3,
                          ),
                        ]
                      : null,
                ),
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Focus(
                  onKeyEvent: _onKey,
                  child: TextField(
                    controller: _controller,
                    focusNode: _focusNode,
                    enabled: widget.enabled,
                    minLines: 1,
                    maxLines: 5,
                    maxLength: ChatInput.maxLength,
                    maxLengthEnforcement: MaxLengthEnforcement.enforced,
                    buildCounter: (
                      context, {
                      required currentLength,
                      required maxLength,
                      required isFocused,
                    }) =>
                        _buildCounter(
                      context,
                      currentLength: currentLength,
                      maxLength: maxLength,
                      isFocused: isFocused,
                    ),
                    textInputAction: TextInputAction.newline,
                    style: AppTheme.body,
                    decoration: InputDecoration(
                      border: InputBorder.none,
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(vertical: 14),
                      hintText: widget.enabled
                          ? widget.hintText
                          : 'Connecting to the assistant...',
                      hintStyle:
                          AppTheme.body.copyWith(color: AppTheme.textFaint),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: AppTheme.spaceSm + 2),
            _SendButton(active: active, onTap: _submit),
          ],
        ),
      ),
    );
  }
}

class _SendButton extends StatelessWidget {
  const _SendButton({required this.active, required this.onTap});

  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      width: 46,
      height: 46,
      decoration: BoxDecoration(
        color: active ? null : AppTheme.surfaceRaised,
        gradient: active ? AppTheme.brandGradient : null,
        borderRadius: BorderRadius.circular(AppTheme.radiusMd + 1),
        boxShadow: active ? AppTheme.shadowLifted : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(AppTheme.radiusMd + 1),
          onTap: active ? onTap : null,
          child: Icon(
            Icons.arrow_upward_rounded,
            color: active ? Colors.black : AppTheme.textMuted,
            size: 22,
          ),
        ),
      ),
    );
  }
}
