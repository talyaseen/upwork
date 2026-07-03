/// Platform seam for browser-only download + rasterization operations.
///
/// The rest of the app imports this file only; the conditional export swaps in
/// the real `dart:html`-backed implementation when compiled for the web and a
/// throwing stub everywhere else (including the Dart VM the tests run on). This
/// keeps `flutter test` fully offline and lets the pure byte-builders in
/// `artifact_download.dart` be unit-tested without a browser.
library;

export 'artifact_platform_stub.dart'
    if (dart.library.html) 'artifact_platform_web.dart';
