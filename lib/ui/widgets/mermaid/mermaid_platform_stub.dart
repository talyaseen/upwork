import 'package:flutter/widgets.dart';

import '../../../models/chat_artifact.dart';

/// Non-web stub: there is no DOM to render into, so signal "cannot render
/// natively" by returning null. The caller then shows the source code-block
/// fallback. This is also the path exercised by widget tests on the VM.
Widget? buildMermaidPlatformView(ChatArtifact artifact, {double height = 320}) =>
    null;
