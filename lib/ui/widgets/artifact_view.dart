import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../models/chat_artifact.dart';
import '../../services/artifact_download.dart';
import 'markdown_body.dart';
import 'mermaid/mermaid_view.dart';

/// Renders a single chat artifact inline beneath an answer: a Mermaid diagram
/// or a code-review Markdown document, each with a download menu.
///
/// Downloads are generated entirely client-side (see [ArtifactDownloader]); on
/// non-web builds the platform seam throws, which is caught here and surfaced
/// as a SnackBar rather than an uncaught error.
class ArtifactView extends StatelessWidget {
  const ArtifactView({
    super.key,
    required this.artifact,
    this.downloader = const ArtifactDownloader(),
  });

  final ChatArtifact artifact;
  final ArtifactDownloader downloader;

  String get _heading {
    final title = artifact.title?.trim();
    if (title != null && title.isNotEmpty) return title;
    return artifact.isDiagram ? 'Diagram' : 'Code / DevOps review';
  }

  IconData get _icon =>
      artifact.isDiagram ? Icons.account_tree_outlined : Icons.rate_review_outlined;

  Future<void> _download(
      BuildContext context, DownloadFormat format) async {
    final messenger = ScaffoldMessenger.maybeOf(context);
    try {
      await downloader.download(artifact, format);
    } catch (e) {
      messenger?.showSnackBar(
        SnackBar(
          content: Text('Could not generate the ${ArtifactDownloader.label(format)} '
              'download. Please try a different format.'),
          backgroundColor: AppTheme.surfaceRaised,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final formats = ArtifactDownloader.formatsFor(artifact);
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: AppTheme.spaceSm + 2),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowSm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 8, 8),
            child: Row(
              children: [
                Icon(_icon, size: 17, color: AppTheme.accent),
                const SizedBox(width: AppTheme.spaceSm),
                Expanded(
                  child: Text(_heading, style: AppTheme.title.copyWith(fontSize: 13)),
                ),
                _DownloadMenu(
                  formats: formats,
                  onSelected: (f) => _download(context, f),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: artifact.isDiagram
                ? MermaidView(artifact: artifact)
                // The backend's `code-review`/`markdown` artifacts carry their
                // full body in `source` (there is no separate wire `markdown`
                // key - see ChatArtifact.fromJson) so fall back to it exactly
                // like ArtifactDownloader.markdownBytes/codeReviewPdf already
                // do; without this fallback the card renders empty even
                // though the review text is right there in `source`.
                : MarkdownBody(
                    markdown: artifact.markdown ?? artifact.source ?? '',
                  ),
          ),
        ],
      ),
    );
  }
}

class _DownloadMenu extends StatelessWidget {
  const _DownloadMenu({required this.formats, required this.onSelected});

  final List<DownloadFormat> formats;
  final ValueChanged<DownloadFormat> onSelected;

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<DownloadFormat>(
      tooltip: 'Download',
      onSelected: onSelected,
      color: AppTheme.surfaceRaised,
      itemBuilder: (context) => [
        for (final f in formats)
          PopupMenuItem<DownloadFormat>(
            value: f,
            child: Row(
              children: [
                const Icon(Icons.download_outlined,
                    size: 16, color: AppTheme.textMuted),
                const SizedBox(width: 8),
                Text(
                  ArtifactDownloader.label(f),
                  style: const TextStyle(
                      color: AppTheme.textPrimary, fontSize: 13),
                ),
              ],
            ),
          ),
      ],
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppTheme.surfaceRaised,
          borderRadius: BorderRadius.circular(AppTheme.radiusSm),
          border: Border.all(color: AppTheme.border),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.download_outlined, size: 15, color: AppTheme.accent),
            const SizedBox(width: AppTheme.spaceXs + 2),
            Text('Download', style: AppTheme.caption.copyWith(
              color: AppTheme.textPrimary,
              fontWeight: FontWeight.w600,
            )),
            const SizedBox(width: 2),
            const Icon(Icons.arrow_drop_down, size: 18, color: AppTheme.textMuted),
          ],
        ),
      ),
    );
  }
}
