import 'package:flutter/material.dart';

import '../core/theme.dart';

Future<bool> showGstInvoiceConfirmationDialog(BuildContext context) async {
  final shouldProceed = await showDialog<bool>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.check_circle_outline, color: AppColors.primaryGreen),
          SizedBox(width: 8),
          Text('GST Invoice'),
        ],
      ),
      content: const Text(
        'GST Billing is enabled.\n\n'
        'The invoice will be generated using the GST details already saved in your Profile.\n\n'
        'Do you want to continue?',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(dialogContext).pop(true),
          child: const Text('Proceed'),
        ),
      ],
    ),
  );

  return shouldProceed ?? false;
}
