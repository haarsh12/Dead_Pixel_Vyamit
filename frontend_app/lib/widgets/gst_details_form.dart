import 'package:flutter/material.dart';

import '../core/gst_billing_details.dart';
import '../core/theme.dart';
import 'gst_state_dropdown.dart';

class GstDetailsForm extends StatefulWidget {
  final GstBillingDetails? initialDetails;
  final ValueChanged<GstBillingDetails> onSave;

  const GstDetailsForm({
    super.key,
    this.initialDetails,
    required this.onSave,
  });

  @override
  State<GstDetailsForm> createState() => _GstDetailsFormState();
}

class _GstDetailsFormState extends State<GstDetailsForm> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _gstinController;
  late final TextEditingController _businessAddressController;
  late final TextEditingController _cityController;
  late final TextEditingController _invoicePrefixController;
  String? _state;
  String? _placeOfSupply;
  GstCalculationMode _calculationMode = GstCalculationMode.cgstSgst;

  @override
  void initState() {
    super.initState();
    final details = widget.initialDetails;
    _gstinController = TextEditingController(text: details?.gstin ?? '');
    _businessAddressController =
        TextEditingController(text: details?.businessAddress ?? '');
    _cityController = TextEditingController(text: details?.city ?? '');
    _invoicePrefixController =
        TextEditingController(text: details?.invoicePrefix ?? '');
    _state = details?.state;
    _placeOfSupply = details?.placeOfSupply;
    _calculationMode =
        details?.calculationMode ?? GstCalculationMode.cgstSgst;
  }

  @override
  void dispose() {
    _gstinController.dispose();
    _businessAddressController.dispose();
    _cityController.dispose();
    _invoicePrefixController.dispose();
    super.dispose();
  }

  void _save() {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    widget.onSave(
      GstBillingDetails(
        gstin: _gstinController.text.trim(),
        businessAddress: _businessAddressController.text.trim(),
        city: _cityController.text.trim(),
        state: _state!,
        placeOfSupply: _placeOfSupply!,
        invoicePrefix: _invoicePrefixController.text.trim(),
        calculationMode: _calculationMode,
      ),
    );
  }

  String? _requiredValidator(String? value, String label) {
    if (value == null || value.trim().isEmpty) {
      return '$label is required';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          const Text(
            'GST Details',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _gstinController,
            maxLength: 15,
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(
              labelText: 'GSTIN Number *',
              counterText: '',
            ),
            validator: (value) => _requiredValidator(value, 'GSTIN number'),
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _businessAddressController,
            minLines: 3,
            maxLines: 4,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(labelText: 'Business Address *'),
            validator: (value) =>
                _requiredValidator(value, 'Business address'),
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _cityController,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(labelText: 'City *'),
            validator: (value) => _requiredValidator(value, 'City'),
          ),
          const SizedBox(height: 16),
          GstStateDropdown(
            label: 'State',
            value: _state,
            onChanged: (value) => setState(() => _state = value),
          ),
          const SizedBox(height: 16),
          GstStateDropdown(
            label: 'Place of Supply',
            value: _placeOfSupply,
            onChanged: (value) => setState(() => _placeOfSupply = value),
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _invoicePrefixController,
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(
              labelText: 'Invoice Prefix',
              hintText: 'INV',
            ),
          ),
          const SizedBox(height: 20),
          const Text(
            'GST Calculation Mode',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          RadioListTile<GstCalculationMode>(
            contentPadding: EdgeInsets.zero,
            title: const Text('CGST + SGST'),
            value: GstCalculationMode.cgstSgst,
            groupValue: _calculationMode,
            activeColor: AppColors.primaryGreen,
            onChanged: (value) {
              if (value != null) {
                setState(() => _calculationMode = value);
              }
            },
          ),
          RadioListTile<GstCalculationMode>(
            contentPadding: EdgeInsets.zero,
            title: const Text('IGST'),
            value: GstCalculationMode.igst,
            groupValue: _calculationMode,
            activeColor: AppColors.primaryGreen,
            onChanged: (value) {
              if (value != null) {
                setState(() => _calculationMode = value);
              }
            },
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _save,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primaryGreen,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              child: const Text('Save GST Details'),
            ),
          ),
        ],
      ),
    );
  }
}
