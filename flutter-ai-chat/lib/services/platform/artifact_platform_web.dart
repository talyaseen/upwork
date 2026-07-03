// This file is compiled only for the web target (selected via the conditional
// export in artifact_platform.dart), so the web-only library lint is expected.
// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;
import 'dart:typed_data';

/// Web implementation of the download/rasterization seam.
///
/// All generation is client-side - there is no server round-trip. Downloads use
/// an object URL + a synthetic anchor click; PNG is produced by drawing the SVG
/// onto an offscreen canvas and reading it back as a PNG data URL.

/// Trigger a browser "save file" for [bytes] under [filename] with [mime].
void downloadBytes(String filename, String mime, Uint8List bytes) {
  final blob = html.Blob(<Object>[bytes], mime);
  final url = html.Url.createObjectUrlFromBlob(blob);
  final anchor = html.AnchorElement(href: url)
    ..download = filename
    ..style.display = 'none';
  html.document.body!.append(anchor);
  anchor.click();
  anchor.remove();
  html.Url.revokeObjectUrl(url);
}

/// Rasterize SVG [svg] to PNG bytes by loading it into an <img> and painting it
/// onto a canvas at [scale]x for a crisp result.
Future<Uint8List> rasterizeSvgToPng(String svg, {double scale = 2}) async {
  final blob = html.Blob(<Object>[svg], 'image/svg+xml');
  final url = html.Url.createObjectUrlFromBlob(blob);
  try {
    final img = html.ImageElement();
    final loaded = img.onLoad.first;
    final errored = img.onError.first;
    img.src = url;
    await Future.any([loaded, errored]);

    // Fall back to sensible defaults if the SVG declares no intrinsic size.
    final w = img.naturalWidth != 0 ? img.naturalWidth : 800;
    final h = img.naturalHeight != 0 ? img.naturalHeight : 600;

    final canvas = html.CanvasElement(
      width: (w * scale).round(),
      height: (h * scale).round(),
    );
    final ctx = canvas.context2D
      ..fillStyle = '#0B0F14'
      ..fillRect(0, 0, canvas.width!, canvas.height!)
      ..scale(scale, scale);
    ctx.drawImage(img, 0, 0);

    final dataUrl = canvas.toDataUrl('image/png');
    final base64 = dataUrl.substring(dataUrl.indexOf(',') + 1);
    return base64Decode(base64);
  } finally {
    html.Url.revokeObjectUrl(url);
  }
}
