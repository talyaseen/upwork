import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../models/chat_artifact.dart';
import 'mermaid_platform.dart';

/// Renders a Mermaid diagram inline.
///
/// On the web it renders the diagram natively (pre-rendered SVG, or mermaid.js
/// from source); on the VM/tests, or when rendering is not possible, it
/// degrades gracefully to a scrollable code block of the Mermaid source.
class MermaidView extends StatelessWidget {
  const MermaidView({super.key, required this.artifact, this.height = 320});

  final ChatArtifact artifact;
  final double height;

  @override
  Widget build(BuildContext context) {
    final native = buildMermaidPlatformView(artifact, height: height);
    if (native != null) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        child: Container(
          height: height,
          width: double.infinity,
          color: Colors.white,
          child: native,
        ),
      );
    }
    return _SourceFallback(source: artifact.source ?? '(no diagram source)');
  }
}

/// The graceful fallback: the Mermaid source in a monospace code block.
class _SourceFallback extends StatelessWidget {
  const _SourceFallback({required this.source});

  final String source;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppTheme.spaceMd),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        border: Border.all(color: AppTheme.border),
      ),
      child: SelectableText(source, style: AppTheme.mono),
    );
  }
}
