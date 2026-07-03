import 'package:flutter/material.dart';

/// Dark product theme for the AI-First Assistant.
///
/// A single source of truth for colour, spacing, radius, elevation and
/// typography so the UI reads as a considered, shipped product - an
/// engineering tool in the register of Linear / Vercel / Raycast (precise,
/// confident, dark-by-default) - rather than default Material scaffolding.
/// Every visual decision below is deliberate; nothing here is a framework
/// default left untouched.
class AppTheme {
  const AppTheme._();

  // ---------------------------------------------------------------------
  // Colour: a 4-step dark "slate" surface scale (never pure black - see
  // background below), one confident primary accent (teal-green - reads as
  // "system healthy / grounded", distinct from default Material indigo), a
  // secondary blue for informational/citation accents, and two semantic
  // states reserved for their single job each (danger, warning).
  // ---------------------------------------------------------------------
  static const Color background = Color(0xFF0A0D12);
  static const Color surface = Color(0xFF12161D);
  static const Color surfaceRaised = Color(0xFF1A2029);
  static const Color surfaceOverlay = Color(0xFF212832); // popovers/menus/hover
  static const Color border = Color(0xFF242C37);
  static const Color borderSubtle = Color(0xFF1A2029);

  // Primary accent ramp (teal-green). accent is the workhorse; accentBright
  // is for hover/pressed states and gradient highlights; accentDim is a flat,
  // pre-computed low-alpha tint for chip/badge fills (kept as a literal
  // rather than a runtime alpha blend so it stays a deliberate, static token).
  static const Color accent = Color(0xFF32D8A4);
  static const Color accentBright = Color(0xFF5CEFC0);
  static const Color accentDim = Color(0xFF15352C);

  // Secondary accent (ocean blue) - citations, links, the user's own bubble.
  static const Color accentAlt = Color(0xFF5B8DEF);
  static const Color userBubble = Color(0xFF2B63D9);

  static const Color textPrimary = Color(0xFFEAF0F6);
  static const Color textMuted = Color(0xFF8C99A8);
  static const Color textFaint = Color(0xFF57626F);

  static const Color danger = Color(0xFFE5534B);
  // Amber, used for the degraded (GPUs offline, repurposed for training) status
  // banner. This backend is GPU-only - there is no CPU serving fallback.
  static const Color warning = Color(0xFFE3B341);

  /// The signature brand mark gradient (top-left -> bottom-right). Repeated
  /// deliberately at exactly three touchpoints - the header mark, the
  /// assistant avatar, and the send button - so the product reads as one
  /// designed system rather than a collection of ad hoc accents.
  static const LinearGradient brandGradient = LinearGradient(
    colors: [accent, accentAlt],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // ---------------------------------------------------------------------
  // Spacing: a 4px base grid. Use these instead of inline magic numbers so
  // rhythm stays consistent across the whole app.
  // ---------------------------------------------------------------------
  static const double spaceXs = 4;
  static const double spaceSm = 8;
  static const double spaceMd = 12;
  static const double spaceLg = 20;
  static const double spaceXl = 32;

  // ---------------------------------------------------------------------
  // Radius: organic, never sharp. A small scale reused everywhere instead of
  // one-off BorderRadius.circular(n) values per widget.
  // ---------------------------------------------------------------------
  static const double radiusSm = 8; // chips, badges, code blocks
  static const double radiusMd = 12; // inputs, buttons, cards
  static const double radiusLg = 16; // message bubbles, panels
  static const double radiusXl = 22; // large surfaces (empty-state mark)
  static const double radiusPill = 999;

  // ---------------------------------------------------------------------
  // Elevation: tinted shadows (never flat grey) so raised surfaces feel like
  // they sit in the same dark, teal-lit space as the rest of the UI. Kept as
  // pre-baked literal colours (not a runtime alpha blend) so they read as
  // deliberate tokens.
  // ---------------------------------------------------------------------
  static const List<BoxShadow> shadowSm = [
    BoxShadow(color: Color(0x33061B15), offset: Offset(0, 2), blurRadius: 8),
  ];
  static const List<BoxShadow> shadowMd = [
    BoxShadow(color: Color(0x40061B15), offset: Offset(0, 6), blurRadius: 20),
  ];
  static const List<BoxShadow> shadowLifted = [
    BoxShadow(color: Color(0x5510352A), offset: Offset(0, 4), blurRadius: 16),
  ];

  // ---------------------------------------------------------------------
  // Typography: a deliberate scale (size + weight + tracking + line-height
  // pairings), not a single flat body size reused everywhere. Weight and
  // letter-spacing carry hierarchy as much as size does. Body copy uses the
  // bundled Roboto family (400/500/700); code/technical content uses the
  // bundled Roboto Mono family so it reads as a distinct, deliberate register
  // rather than falling back to a generic platform monospace font.
  // ---------------------------------------------------------------------
  static const String fontFamily = 'Roboto';
  static const String monoFontFamily = 'RobotoMono';

  static const TextStyle headline = TextStyle(
    fontFamily: fontFamily,
    fontSize: 20,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.3,
    height: 1.25,
    color: textPrimary,
  );

  static const TextStyle title = TextStyle(
    fontFamily: fontFamily,
    fontSize: 15,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.1,
    height: 1.3,
    color: textPrimary,
  );

  static const TextStyle body = TextStyle(
    fontFamily: fontFamily,
    fontSize: 14.5,
    fontWeight: FontWeight.w400,
    height: 1.5,
    color: textPrimary,
  );

  static const TextStyle bodyStrong = TextStyle(
    fontFamily: fontFamily,
    fontSize: 14.5,
    fontWeight: FontWeight.w600,
    height: 1.5,
    color: textPrimary,
  );

  static const TextStyle label = TextStyle(
    fontFamily: fontFamily,
    fontSize: 11,
    fontWeight: FontWeight.w700,
    letterSpacing: 1.1,
    color: textMuted,
  );

  static const TextStyle caption = TextStyle(
    fontFamily: fontFamily,
    fontSize: 12,
    fontWeight: FontWeight.w500,
    height: 1.4,
    color: textMuted,
  );

  static const TextStyle mono = TextStyle(
    fontFamily: monoFontFamily,
    fontSize: 12.5,
    fontWeight: FontWeight.w400,
    height: 1.55,
    color: textPrimary,
  );

  static ThemeData build() {
    final base = ThemeData.dark(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        surface: surface,
        primary: accent,
        secondary: accentAlt,
        error: danger,
        onPrimary: Color(0xFF06231A),
        onSurface: textPrimary,
      ),
      textTheme: base.textTheme.apply(
        bodyColor: textPrimary,
        displayColor: textPrimary,
        fontFamily: fontFamily,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        shadowColor: Color(0x40061B15),
        elevation: 6,
        centerTitle: false,
      ),
      dividerColor: border,
    );
  }
}
