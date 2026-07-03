/// A backend failure surfaced to the UI in a user-readable form.
///
/// The service layer catches transport and protocol errors and rethrows them
/// as [BackendException] so the UI never has to know about HTTP status codes,
/// sockets or JSON parsing.
class BackendException implements Exception {
  const BackendException(this.message, {this.isAuth = false});

  final String message;

  /// True when the failure was an authentication problem, so the UI can offer
  /// a "retry sign-in" affordance instead of a generic error.
  final bool isAuth;

  @override
  String toString() => 'BackendException: $message';
}
