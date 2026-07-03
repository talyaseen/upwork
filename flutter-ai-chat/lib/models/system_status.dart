import 'package:flutter/foundation.dart';

/// The raw payload of the public `GET /api/status` health endpoint.
///
/// Contract (built against, and mocked in tests). This backend is GPU-only:
/// there is no CPU serving tier, so `tier` is `"gpu"` when the GPUs are up and
/// `"offline"` when they have been repurposed (no answers are served):
/// ```json
/// {"tier": "gpu" | "offline",
///  "gpu_online": true | false,
///  "model": "<string>"}
/// ```
///
/// This is a pure data object. How it maps onto a banner colour and label lives
/// in the state layer ([StatusController]), and how that is drawn lives in the
/// UI layer, so the wire shape never leaks past this class.
@immutable
class SystemStatus {
  const SystemStatus({
    required this.tier,
    required this.gpuOnline,
    required this.model,
  });

  /// Which serving state is active: `gpu` when the GPUs are up, `offline` when
  /// they have been repurposed for training.
  final String tier;

  /// True when the GPU serving tier is up and answering; false when the GPUs
  /// have been repurposed for training. This backend is GPU-only, so `false`
  /// means no answers are available (there is no CPU fallback).
  final bool gpuOnline;

  /// The model currently answering, for display/diagnostics.
  final String model;

  factory SystemStatus.fromJson(Map<String, dynamic> json) {
    return SystemStatus(
      tier: json['tier'] as String? ?? '',
      gpuOnline: json['gpu_online'] as bool? ?? false,
      model: json['model'] as String? ?? '',
    );
  }
}
