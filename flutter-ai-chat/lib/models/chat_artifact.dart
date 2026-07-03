import 'package:flutter/foundation.dart';

/// The kind of rich artifact a skill attached to an assistant answer.
enum ArtifactKind {
  /// A Mermaid diagram (carries [ChatArtifact.source], and optionally a
  /// pre-rendered [ChatArtifact.svg]).
  mermaid,

  /// Generic Markdown content ([ChatArtifact.markdown]). This is also what
  /// the backend's code-review skill emits on the wire (`kind: "markdown"`,
  /// see `chat_service.py`'s `ArtifactEvent(kind="markdown", ...)`) - there is
  /// no separate `"code-review"` wire kind, so there is deliberately no
  /// dedicated enum value for it. Every UI consumer already distinguishes
  /// "diagram" vs "everything else" via [ChatArtifact.isDiagram] rather than
  /// branching on the specific kind, so a dedicated value would be
  /// unreachable dead weight (a prior `codeReview` value was removed for
  /// exactly this reason - confirmed by grepping the backend for every place
  /// an artifact `kind` is set: only `"mermaid"` and `"markdown"` are ever
  /// emitted).
  markdown,

  /// An unrecognised type; rendered as plain text so the UI degrades safely.
  unknown,
}

/// A rich artifact emitted alongside the streamed answer.
///
/// The backend's mermaid skill returns the Mermaid [source] and may include a
/// pre-rendered [svg]; the code-review skill returns [markdown]. Modelled as one
/// value object so the UI can decide how to render and which downloads to offer
/// without re-reading the wire format.
@immutable
class ChatArtifact {
  const ChatArtifact({
    required this.kind,
    this.title,
    this.source,
    this.svg,
    this.markdown,
    this.downloads = const [],
  });

  final ArtifactKind kind;

  /// Optional human label, used for the download filename and the card header.
  final String? title;

  /// Mermaid source text (for [ArtifactKind.mermaid]).
  final String? source;

  /// Pre-rendered SVG markup, when the backend supplied one.
  final String? svg;

  /// Markdown body (for code-review / markdown artifacts).
  final String? markdown;

  /// The download formats the backend offers for this artifact, verbatim and
  /// in priority order (e.g. `["pdf", "svg", "png", "mmd"]`) - see
  /// `ArtifactEvent.downloads` in `chat_service.py`. `ArtifactDownloader`
  /// reads this directly instead of guessing per-kind, so the client's
  /// download menu can never drift out of sync with what the backend sends.
  final List<String> downloads;

  bool get isDiagram => kind == ArtifactKind.mermaid;
  bool get hasSvg => svg != null && svg!.trim().isNotEmpty;

  static ArtifactKind kindFromString(String? raw) {
    switch (raw) {
      case 'mermaid':
        return ArtifactKind.mermaid;
      case 'markdown':
        return ArtifactKind.markdown;
      default:
        return ArtifactKind.unknown;
    }
  }

  /// Parse the backend's `event: artifact` SSE payload (see
  /// `ChatArtifactEvent` in the FastAPI backend's `app/schemas/chat.py`, and
  /// `chat_service.py`'s ``ArtifactEvent`` yields). The wire key for the
  /// artifact kind is `kind` (e.g. `"mermaid"` or `"markdown"`) - NOT `type`.
  /// A previous version of this parser read `json['type']`, which the backend
  /// never sends, so every artifact silently decoded as [ArtifactKind.unknown]
  /// regardless of its real kind (see the regression test in
  /// `test/fastapi_backend_test.dart`).
  factory ChatArtifact.fromJson(Map<String, dynamic> json) {
    return ChatArtifact(
      kind: kindFromString(json['kind'] as String?),
      title: json['title'] as String?,
      source: json['source'] as String?,
      svg: json['svg'] as String?,
      markdown: json['markdown'] as String?,
      downloads: (json['downloads'] as List<dynamic>?)
              ?.whereType<String>()
              .toList() ??
          const [],
    );
  }
}
