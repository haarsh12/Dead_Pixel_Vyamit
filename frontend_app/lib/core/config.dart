import 'dart:io';
import 'package:flutter/foundation.dart';

class ApiConfig {
  // 🚀 PRODUCTION - Render Backend
  static const String _productionUrl = "    ";

  // 🧪 LOCAL DEVELOPMENT URLs (only used when uncommenting local dev code below)
  static const String _emulatorUrl = "http://10.0.2.2:8000";
  static const String _realDeviceUrl = "http://10.231.114.205:8000";  // Replace with your laptop's local IP for local testing
  static const String _localUrl = "http://localhost:8000";

  static String get baseUrl {
    // 🧪 DEVELOPMENT MODE - Local Backend
    if (kReleaseMode) {
      return _productionUrl;  // Use production in release mode
    }

    if (Platform.isAndroid) {
      return _realDeviceUrl;  // Real phone connected via USB
      // return _emulatorUrl;  // Uncomment for emulator
    }

    return _localUrl;  // Web/Windows
    
    // 🚀 PRODUCTION MODE - Uncomment below for production:
    /*
    return _productionUrl;
    */
  }

  /// Convert http/https baseUrl to ws/wss wsUrl for continuous WebSocket connection
  static String get wsUrl {
    final base = baseUrl;
    if (base.startsWith('https://')) {
      return base.replaceFirst('https://', 'wss://');
    } else if (base.startsWith('http://')) {
      return base.replaceFirst('http://', 'ws://');
    }
    return 'ws://$base';
  }
}
