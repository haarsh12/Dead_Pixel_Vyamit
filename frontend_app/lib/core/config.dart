import 'package:flutter/foundation.dart';

class ApiConfig {
  /// Configure the deployed backend at build time, for example:
  /// flutter build apk --dart-define=API_BASE_URL=https://api.example.com
  static const String _configuredUrl = String.fromEnvironment('API_BASE_URL');

  // Local development defaults. A physical Android device should use
  // API_BASE_URL with the computer's reachable LAN address.
  static const String _emulatorUrl = 'http://10.0.2.2:8000';
  static const String _localUrl = 'http://localhost:8000';

  static String get baseUrl {
    final configured = _configuredUrl.trim();
    if (configured.isNotEmpty) {
      return configured.replaceFirst(RegExp(r'/+$'), '');
    }

    if (kReleaseMode) {
      throw StateError('API_BASE_URL must be supplied for a release build.');
    }

    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return _emulatorUrl;
    }
    return _localUrl;
  }

  /// Convert the HTTP API origin to its matching WebSocket origin.
  static String get wsUrl {
    final base = baseUrl;
    if (base.startsWith('https://')) {
      return base.replaceFirst('https://', 'wss://');
    }
    if (base.startsWith('http://')) {
      return base.replaceFirst('http://', 'ws://');
    }
    return 'ws://$base';
  }
}
