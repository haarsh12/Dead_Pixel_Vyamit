import 'package:flutter/material.dart';

import '../core/theme.dart';

class GstToggleButton extends StatelessWidget {
  final bool isEnabled;
  final ValueChanged<bool> onChanged;

  const GstToggleButton({
    super.key,
    required this.isEnabled,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final foregroundColor = isEnabled ? Colors.white : Colors.grey[600]!;
    final backgroundColor = isEnabled ? AppColors.primaryGreen : Colors.grey[100]!;

    return Semantics(
      button: true,
      toggled: isEnabled,
      label: 'GST',
      child: InkWell(
        onTap: () => onChanged(!isEnabled),
        borderRadius: BorderRadius.circular(18),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeInOut,
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
          decoration: BoxDecoration(
            color: backgroundColor,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: isEnabled ? AppColors.primaryGreen : Colors.grey[400]!,
            ),
          ),
          child: AnimatedDefaultTextStyle(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeInOut,
            style: TextStyle(
              color: foregroundColor,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
            child: const Text('GST'),
          ),
        ),
      ),
    );
  }
}
