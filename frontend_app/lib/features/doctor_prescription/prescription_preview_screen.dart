import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../models/shop_details.dart';
import 'models/prescription_draft.dart';
import 'services/doctor_prescription_printer_service.dart';
import 'services/doctor_prescription_service.dart';
import 'widgets/doctor_signature_pad.dart';

class PrescriptionPreviewScreen extends StatefulWidget {
  final PrescriptionDraft initialDraft;
  final ShopDetails shopDetails;
  final bool isPrinterConnected;
  final VoidCallback togglePrinter;

  const PrescriptionPreviewScreen({
    super.key,
    required this.initialDraft,
    required this.shopDetails,
    required this.isPrinterConnected,
    required this.togglePrinter,
  });

  @override
  State<PrescriptionPreviewScreen> createState() =>
      _PrescriptionPreviewScreenState();
}

class _PrescriptionPreviewScreenState extends State<PrescriptionPreviewScreen> {
  final _formKey = GlobalKey<FormState>();
  final _signatureKey = GlobalKey<DoctorSignaturePadState>();
  final _printer = DoctorPrescriptionPrinterService();
  final _service = DoctorPrescriptionService();
  late final TextEditingController _patientName;
  late final TextEditingController _patientAge;
  late final TextEditingController _patientGender;
  late final TextEditingController _patientPhone;
  late final TextEditingController _diagnosis;
  late final TextEditingController _notes;
  late DateTime _prescribedAt;
  late List<_MedicationForm> _medications;
  bool _isPrinting = false;

  @override
  void initState() {
    super.initState();
    final draft = widget.initialDraft;
    _patientName = TextEditingController(text: draft.patientName);
    _patientAge =
        TextEditingController(text: draft.patientAge?.toString() ?? '');
    _patientGender = TextEditingController(text: draft.patientGender);
    _patientPhone = TextEditingController(text: draft.patientPhone);
    _diagnosis = TextEditingController(text: draft.diagnosis);
    _notes = TextEditingController(text: draft.additionalNotes);
    _prescribedAt = draft.prescribedAt;
    _medications =
        draft.medications.map(_MedicationForm.fromMedication).toList();
    if (_medications.isEmpty) _medications = [_MedicationForm.empty()];
  }

  @override
  void dispose() {
    _patientName.dispose();
    _patientAge.dispose();
    _patientGender.dispose();
    _patientPhone.dispose();
    _diagnosis.dispose();
    _notes.dispose();
    for (final medication in _medications) {
      medication.dispose();
    }
    super.dispose();
  }

  Future<void> _pickDateTime() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _prescribedAt,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
        context: context, initialTime: TimeOfDay.fromDateTime(_prescribedAt));
    if (time == null || !mounted) return;
    setState(() => _prescribedAt =
        DateTime(date.year, date.month, date.day, time.hour, time.minute));
  }

  PrescriptionDraft _buildDraft() {
    return PrescriptionDraft(
      patientName: _patientName.text,
      patientAge: int.tryParse(_patientAge.text.trim()),
      patientGender: _patientGender.text,
      patientPhone: _patientPhone.text,
      diagnosis: _diagnosis.text,
      additionalNotes: _notes.text,
      prescribedAt: _prescribedAt,
      medications: _medications.map((item) => item.toMedication()).toList(),
    );
  }

  Future<bool> _askToSavePatient() async {
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Add to patient list?'),
            content: const Text(
              'The prescription has printed. Would you like to save this patient in your searchable patient list for future visits?',
            ),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Not now')),
              ElevatedButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('Add patient')),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _print() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final registration = widget.shopDetails.medicalRegistrationNumber.trim();
    if (registration.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text(
                'Add the medical registration number in Profile before printing.')),
      );
      return;
    }
    if (!widget.isPrinterConnected) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Connect the 58 mm printer first.')),
      );
      widget.togglePrinter();
      return;
    }
    // Confirm the server-side doctor profile immediately before the physical
    // print. This prevents a stale local profile from producing a prescription
    // with an old or removed medical registration number.
    Map<String, dynamic> readiness;
    try {
      readiness = await _service.profileReadiness();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text(
                  'Could not verify the doctor profile. Check the connection and try again.')),
        );
      }
      return;
    }
    if (readiness['can_print'] != true) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text(
                  'Add a medical registration number in Profile before printing.')),
        );
      }
      return;
    }
    setState(() => _isPrinting = true);
    final draft = _buildDraft();
    try {
      final signaturePng = await _signatureKey.currentState?.exportPng();
      final result = await _printer.printPrescription(
        draft,
        DoctorProfileSnapshot(
          doctorName:
              readiness['doctor_name']?.toString() ?? widget.shopDetails.ownerName,
          clinicName: widget.shopDetails.shopName,
          qualifications: readiness['qualifications']?.toString() ??
              widget.shopDetails.qualifications,
          medicalRegistrationNumber:
              readiness['medical_registration_number']?.toString() ?? registration,
          address: widget.shopDetails.address,
          phone: widget.shopDetails.phone1,
        ),
        signaturePng: signaturePng,
      );
      if (result != 'Success') {
        if (mounted)
          ScaffoldMessenger.of(context)
              .showSnackBar(SnackBar(content: Text(result)));
        return;
      }

      if (!mounted) return;
      final savePatient = await _askToSavePatient();
      await _service.recordPrintedPrescription(
        draft,
        signatureStrokes: _signatureKey.currentState?.strokeData ?? const [],
        savePatient: savePatient,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(savePatient
                ? 'Prescription printed and patient saved.'
                : 'Prescription printed and saved to history.')),
      );
      Navigator.of(context).pop();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text(
                  'Printed, but the history record could not be saved. Please check your connection.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isPrinting = false);
    }
  }

  String get _dateLabel {
    final date = _prescribedAt;
    final day = date.day.toString().padLeft(2, '0');
    final month = date.month.toString().padLeft(2, '0');
    final hour = date.hour.toString().padLeft(2, '0');
    final minute = date.minute.toString().padLeft(2, '0');
    return '$day/$month/${date.year}  $hour:$minute';
  }

  @override
  Widget build(BuildContext context) {
    const blue = Color(0xFF1B7A9B);
    return Scaffold(
      backgroundColor: const Color(0xFFF5F8F9),
      appBar: AppBar(
        title: const Text('Review prescription'),
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF17324A),
        actions: [
          IconButton(
            tooltip: 'Connect printer',
            icon: Icon(Icons.print_rounded,
                color: widget.isPrinterConnected
                    ? AppColors.printerConnected
                    : AppColors.printerDisconnected),
            onPressed: widget.togglePrinter,
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
          children: [
            Container(
              padding: const EdgeInsets.all(15),
              decoration: BoxDecoration(
                  color: const Color(0xFFEAF7FB),
                  borderRadius: BorderRadius.circular(14)),
              child: const Text(
                  'Review and edit every field before printing. The print is formatted vertically for a 57–58 mm thermal printer.'),
            ),
            const SizedBox(height: 16),
            _section('Doctor', [
              _readOnly('Doctor name', widget.shopDetails.ownerName),
              _readOnly(
                  'Qualifications',
                  widget.shopDetails.qualifications.isEmpty
                      ? 'Add in Profile'
                      : widget.shopDetails.qualifications),
              _readOnly(
                  'Medical registration no.',
                  widget.shopDetails.medicalRegistrationNumber.isEmpty
                      ? 'Required in Profile'
                      : widget.shopDetails.medicalRegistrationNumber),
            ]),
            _section('Patient details', [
              _field('Patient name', _patientName, isRequired: true),
              Row(children: [
                Expanded(
                    child: _field('Age', _patientAge,
                        keyboardType: TextInputType.number)),
                const SizedBox(width: 12),
                Expanded(child: _field('Gender', _patientGender)),
              ]),
              _field('Phone (optional)', _patientPhone,
                  keyboardType: TextInputType.phone),
              _field('Disease / diagnosis', _diagnosis),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.calendar_today_outlined, color: blue),
                title: const Text('Prescription date & time'),
                subtitle: Text(_dateLabel),
                trailing: const Icon(Icons.edit_outlined),
                onTap: _pickDateTime,
              ),
            ]),
            _section('Medicines', [
              ..._medications
                  .asMap()
                  .entries
                  .map((entry) => _medicineEditor(entry.key, entry.value)),
              OutlinedButton.icon(
                onPressed: () =>
                    setState(() => _medications.add(_MedicationForm.empty())),
                icon: const Icon(Icons.add),
                label: const Text('Add medicine'),
              ),
            ]),
            _section('Additional advice',
                [_field('Advice / instructions', _notes, maxLines: 3)]),
            _section('Doctor signature', [
              Row(
                children: [
                  const Expanded(
                      child:
                          Text('Sign in the box using your finger or stylus.')),
                  TextButton.icon(
                    onPressed: () => _signatureKey.currentState?.clear(),
                    icon: const Icon(Icons.delete_outline),
                    label: const Text('Clear'),
                  ),
                ],
              ),
              Container(
                color: Colors.white,
                child: DoctorSignaturePad(key: _signatureKey),
              ),
            ]),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: ElevatedButton.icon(
            onPressed: _isPrinting ? null : _print,
            icon: _isPrinting
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                        color: Colors.white, strokeWidth: 2))
                : const Icon(Icons.print_rounded),
            label: Text(_isPrinting ? 'Printing…' : 'Print prescription'),
            style: ElevatedButton.styleFrom(
                backgroundColor: blue,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16)),
          ),
        ),
      ),
    );
  }

  Widget _section(String title, List<Widget> children) => Card(
        margin: const EdgeInsets.only(bottom: 15),
        elevation: 0,
        color: Colors.white,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: const BorderSide(color: Color(0xFFE0E8EB))),
        child: Padding(
          padding: const EdgeInsets.all(15),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title,
                style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                    color: Color(0xFF17324A))),
            const SizedBox(height: 12),
            ...children,
          ]),
        ),
      );

  Widget _readOnly(String label, String value) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text.rich(TextSpan(children: [
          TextSpan(
              text: '$label: ',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          TextSpan(text: value)
        ])),
      );

  Widget _field(
    String label,
    TextEditingController controller, {
    bool isRequired = false,
    TextInputType? keyboardType,
    int maxLines = 1,
  }) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextFormField(
          controller: controller,
          keyboardType: keyboardType,
          maxLines: maxLines,
          validator: isRequired
              ? (value) => value == null || value.trim().isEmpty
                  ? '$label is required'
                  : null
              : null,
          decoration: InputDecoration(
              labelText: label,
              border: const OutlineInputBorder(),
              isDense: true),
        ),
      );

  Widget _medicineEditor(int index, _MedicationForm medication) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: const Color(0xFFF8FBFC),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFDCE9ED))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text('Medicine ${index + 1}',
                style: const TextStyle(fontWeight: FontWeight.w700)),
            const Spacer(),
            if (_medications.length > 1)
              IconButton(
                tooltip: 'Remove medicine',
                onPressed: () => setState(() {
                  final removed = _medications.removeAt(index);
                  removed.dispose();
                }),
                icon: const Icon(Icons.remove_circle_outline,
                    color: Colors.redAccent),
              ),
          ]),
          _field('Medicine name', medication.name, isRequired: true),
          Row(children: [
            Expanded(child: _field('Dose', medication.dose)),
            const SizedBox(width: 10),
            Expanded(child: _field('Route', medication.route)),
          ]),
          _field('Frequency / times per day', medication.frequency),
          Row(children: [
            Expanded(child: _field('Duration', medication.duration)),
            const SizedBox(width: 10),
            Expanded(child: _field('Before / after food', medication.timing)),
          ]),
          _field('Medicine instructions', medication.instructions, maxLines: 2),
        ]),
      );
}

class _MedicationForm {
  final TextEditingController name;
  final TextEditingController dose;
  final TextEditingController frequency;
  final TextEditingController duration;
  final TextEditingController timing;
  final TextEditingController route;
  final TextEditingController instructions;

  _MedicationForm({
    required this.name,
    required this.dose,
    required this.frequency,
    required this.duration,
    required this.timing,
    required this.route,
    required this.instructions,
  });

  factory _MedicationForm.empty() =>
      _MedicationForm.fromMedication(PrescriptionMedication());

  factory _MedicationForm.fromMedication(PrescriptionMedication value) =>
      _MedicationForm(
        name: TextEditingController(text: value.name),
        dose: TextEditingController(text: value.dose),
        frequency: TextEditingController(text: value.frequency),
        duration: TextEditingController(text: value.duration),
        timing: TextEditingController(text: value.timing),
        route: TextEditingController(text: value.route),
        instructions: TextEditingController(text: value.instructions),
      );

  PrescriptionMedication toMedication() => PrescriptionMedication(
        name: name.text,
        dose: dose.text,
        frequency: frequency.text,
        duration: duration.text,
        timing: timing.text,
        route: route.text,
        instructions: instructions.text,
      );

  void dispose() {
    name.dispose();
    dose.dispose();
    frequency.dispose();
    duration.dispose();
    timing.dispose();
    route.dispose();
    instructions.dispose();
  }
}
