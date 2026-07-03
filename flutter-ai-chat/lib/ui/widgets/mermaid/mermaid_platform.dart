import 'package:flutter/widgets.dart';

import '../../../models/chat_artifact.dart';

/// Platform seam for natively rendering a Mermaid diagram in the browser.
///
/// Returns a widget that renders the diagram (a pre-rendered SVG, or a
/// mermaid.js-rendered source) on the web, and `null` everywhere else (the VM
/// the tests run on), so the caller falls back to a source code block. The
/// conditional export keeps `dart:html`/`dart:ui_web` out of the VM build.
export 'mermaid_platform_stub.dart'
    if (dart.library.html) 'mermaid_platform_web.dart';

/// The signature both implementations provide:
///   Widget? buildMermaidPlatformView(ChatArtifact artifact, {double height});
typedef MermaidViewBuilder = Widget? Function(
  ChatArtifact artifact, {
  double height,
});
