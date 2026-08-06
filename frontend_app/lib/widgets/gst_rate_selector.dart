import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme.dart';

class GstRateSelector extends StatefulWidget {
  final double? initialRate;
  final TextEditingController customRateController;
  final bool showCustomRateError;
  final void Function(double? rate, bool isCustom) onSelectionChanged;

  const GstRateSelector({
    super.key,
    required this.initialRate,
    required this.customRateController,
    required this.showCustomRateError,
    required this.onSelectionChanged,
  });

  @override
  State<GstRateSelector> createState() => _GstRateSelectorState();
}

class _GstRateSelectorState extends State<GstRateSelector> {
  static const _presetRates = [5.0, 12.0, 18.0, 28.0];
  late double? _selectedRate;
  late bool _isCustomRate;

  @override
  void initState() {
    super.initState();
    _selectedRate = _presetRates.contains(widget.initialRate)
        ? widget.initialRate
        : null;
    _isCustomRate = widget.initialRate != null && _selectedRate == null;
    if (_isCustomRate && widget.customRateController.text.isEmpty) {
      widget.customRateController.text = _formatRate(widget.initialRate!);
    }
  }

  String _formatRate(double rate) => rate == rate.roundToDouble()
      ? rate.toInt().toString()
      : rate.toString();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('GST Rate',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            ..._presetRates.map((rate) => ChoiceChip(
                  label: Text('${_formatRate(rate)}%'),
                  selected: !_isCustomRate && _selectedRate == rate,
                  selectedColor: AppColors.lightGreenBg,
                  onSelected: (selected) {
                    setState(() {
                      _isCustomRate = false;
                      _selectedRate = selected ? rate : null;
                    });
                    widget.onSelectionChanged(_selectedRate, false);
                  },
                )),
            ChoiceChip(
              label: const Text('Custom GST'),
              selected: _isCustomRate,
              selectedColor: AppColors.lightGreenBg,
              onSelected: (selected) {
                setState(() {
                  _isCustomRate = selected;
                  _selectedRate = null;
                  if (!selected) widget.customRateController.clear();
                });
                widget.onSelectionChanged(null, selected);
              },
            ),
          ],
        ),
        AnimatedSize(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeInOut,
          child: _isCustomRate
              ? Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: TextField(
                    controller: widget.customRateController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    inputFormatters: [
                      TextInputFormatter.withFunction((oldValue, newValue) =>
                          RegExp(r'^\d*\.?\d*$').hasMatch(newValue.text)
                              ? newValue
                              : oldValue),
                    ],
                    onChanged: (_) => widget.onSelectionChanged(null, true),
                    decoration: InputDecoration(
                      labelText: 'Custom GST % *',
                      errorText: widget.showCustomRateError
                          ? 'Enter a valid GST rate'
                          : null,
                    ),
                  ),
                )
              : const SizedBox.shrink(),
        ),
      ],
    );
  }
}
