// This file is compiled only for the web target (selected via the conditional
// export in mermaid_platform.dart), so the web-only library lint is expected.
// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'dart:js' as js;
import 'dart:ui_web' as ui_web;

import 'package:flutter/widgets.dart';

import '../../../models/chat_artifact.dart';

/// Web implementation: render a Mermaid diagram client-side.
///
/// Strategy (documented choice): prefer the SVG the backend pre-rendered and
/// inject it directly into a platform view - this needs no JS library and is
/// the most robust path. When only Mermaid source is present, fall back to
/// mermaid.js (loaded from web/index.html) to render it in the browser. If
/// neither is available, return null so the caller shows a source code block.
final Set<String> _registered = <String>{};
int _seq = 0;

Widget? buildMermaidPlatformView(ChatArtifact artifact, {double height = 320}) {
  final hasSvg = artifact.hasSvg;
  final source = artifact.source;
  if (!hasSvg && (source == null || source.trim().isEmpty)) return null;

  // A stable-per-content view type, so identical diagrams reuse one factory.
  final viewType =
      'mermaid-${artifact.hashCode}-${(artifact.svg ?? source).hashCode}';

  if (!_registered.contains(viewType)) {
    _registered.add(viewType);
    ui_web.platformViewRegistry.registerViewFactory(viewType, (int viewId) {
      final container = html.DivElement()
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.overflow = 'auto'
        ..style.display = 'flex'
        ..style.alignItems = 'center'
        ..style.justifyContent = 'center';

      if (hasSvg) {
        container.setInnerHtml(
          artifact.svg!,
          treeSanitizer: html.NodeTreeSanitizer.trusted,
        );
      } else {
        final id = 'mermaid-node-${_seq++}';
        final node = html.DivElement()
          ..id = id
          ..className = 'mermaid'
          ..text = source!;
        container.append(node);
        // Render after the node is attached to the DOM.
        html.window.requestAnimationFrame((_) => _renderMermaid(node));
      }
      return container;
    });
  }

  return SizedBox(
    height: height,
    child: HtmlElementView(viewType: viewType),
  );
}

/// Best-effort mermaid.js invocation, tolerant of API differences across
/// mermaid versions and of the script not being present.
void _renderMermaid(html.Element node) {
  try {
    final mermaid = js.context['mermaid'];
    if (mermaid == null) return;
    try {
      mermaid.callMethod('run', [
        js.JsObject.jsify({
          'nodes': [node]
        })
      ]);
    } catch (_) {
      // Older API: mermaid.init(undefined, node)
      mermaid.callMethod('init', [null, node]);
    }
  } catch (_) {
    // Leave the raw source visible rather than throwing into the UI.
  }
}
