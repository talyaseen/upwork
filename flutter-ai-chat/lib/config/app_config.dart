/// Application configuration, resolved at build time.
///
/// The backend base URL is injected with `--dart-define` so the same build can
/// be repointed at a local backend, a staging host or production without a code
/// change:
///
/// ```
/// flutter build web --dart-define=API_BASE_URL=https://api.example.com
/// ```
///
/// It is never hardcoded into the UI or service layer. The localhost default
/// keeps the app runnable out of the box during local development.
class AppConfig {
  const AppConfig._();

  /// Product branding shown in the app bar and window title.
  static const String appName = 'AI-First Assistant';
  static const String appTagline = 'Grounded answers with sources you can check';

  /// Base URL of the REST backend. Override with:
  /// `--dart-define=API_BASE_URL=http://host:port`.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '/api',
  );

  /// Credentials for the transparent demo account. The app auto-provisions
  /// this account on startup (register-or-login) so any visitor can chat with
  /// zero login friction. These are demo-only, non-sensitive values and carry
  /// no access to anything beyond the public seed corpus.
  static const String demoUsername = String.fromEnvironment(
    'DEMO_USERNAME',
    defaultValue: 'demo_visitor',
  );
  static const String demoPassword = String.fromEnvironment(
    'DEMO_PASSWORD',
    defaultValue: 'demo-visitor-pass-2026',
  );
}
