import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../core/gst_billing_details.dart';
import 'gst_details_form.dart';

class GstBillingSection extends StatelessWidget {
  final bool isEnabled;
  final GstBillingDetails? details;
  final ValueChanged<bool> onEnabledChanged;
  final ValueChanged<GstBillingDetails> onSave;

  const GstBillingSection({
    super.key,
    required this.isEnabled,
    required this.details,
    required this.onEnabledChanged,
    required this.onSave,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'GST Billing',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        Align(
          alignment: Alignment.centerRight,
          child: Switch(
            value: isEnabled,
            activeColor: AppColors.primaryGreen,
            onChanged: onEnabledChanged,
          ),
        ),
        AnimatedSize(
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeInOut,
          alignment: Alignment.topCenter,
          child: isEnabled
              ? GstDetailsForm(initialDetails: details, onSave: onSave)
              : const SizedBox.shrink(),
        ),
      ],
    );
  }
}
