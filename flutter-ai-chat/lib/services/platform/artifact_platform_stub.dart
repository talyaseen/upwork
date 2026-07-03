import 'dart:typed_data';

/// Non-web stub. These operations rely on browser APIs (Blob, anchor download,
/// canvas); on the Dart VM they are never reached at runtime (the UI only calls
/// them from the web build), so they throw a clear error if invoked.

void downloadBytes(String filename, String mime, Uint8List bytes) {
  throw UnsupportedError(
    'File downloads are only available on the web build of this app.',
  );
}

Future<Uint8List> rasterizeSvgToPng(String svg, {double scale = 2}) {
  throw UnsupportedError(
    'SVG to PNG rasterization is only available on the web build of this app.',
  );
}
