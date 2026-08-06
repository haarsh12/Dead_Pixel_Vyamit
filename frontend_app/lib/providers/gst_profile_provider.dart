import 'package:flutter/material.dart';

import '../core/gst_billing_details.dart';

/// Holds GST form values for the current app session only.
/// Backend persistence will be added after its API contract is available.
class GstProfileProvider with ChangeNotifier {
  bool _isEnabled = false;
  GstBillingDetails? _details;

  bool get isEnabled => _isEnabled;
  GstBillingDetails? get details => _details;

  void setEnabled(bool value) {
    _isEnabled = value;
    notifyListeners();
  }

  void saveDetails(GstBillingDetails details) {
    _details = details;
    notifyListeners();
  }
}
