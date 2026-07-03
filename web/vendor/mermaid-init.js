// Initializes the self-hosted mermaid.min.js. Kept as its own same-origin file
// (rather than an inline <script>) so the page can run under a strict
// Content-Security-Policy with script-src 'self' and no 'unsafe-inline'.
//
// startOnLoad is false: the Flutter app renders each diagram on demand from its
// platform view (see lib/ui/widgets/mermaid/mermaid_platform_web.dart).
//
// suppressErrorRendering is true: the 7B model frequently emits syntactically
// invalid Mermaid, and by default mermaid.js injects a red "Syntax error"
// bomb graphic into the card - a scary, broken-looking artifact for a
// prospect. With this flag mermaid throws instead of rendering that graphic,
// the render helper catches it, and the card falls back gracefully to the raw
// Mermaid source (see mermaid_platform_web.dart's _renderMermaid).
if (window.mermaid) {
  window.mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    suppressErrorRendering: true,
  });
}
