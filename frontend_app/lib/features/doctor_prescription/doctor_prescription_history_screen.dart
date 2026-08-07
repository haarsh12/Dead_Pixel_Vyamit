import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/theme.dart';
import 'services/doctor_prescription_service.dart';

class DoctorPrescriptionHistoryScreen extends StatefulWidget {
  const DoctorPrescriptionHistoryScreen({super.key});

  @override
  State<DoctorPrescriptionHistoryScreen> createState() =>
      _DoctorPrescriptionHistoryScreenState();
}

class _DoctorPrescriptionHistoryScreenState
    extends State<DoctorPrescriptionHistoryScreen> {
  final _service = DoctorPrescriptionService();
  List<Map<String, dynamic>> _records = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final records = await _service.history();
      if (mounted) setState(() => _records = records);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Unable to load prescription history.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _deleteRecord(Map<String, dynamic> record) async {
    final prescriptionId = record['id'] as int?;
    if (prescriptionId == null) return;
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Delete prescription?'),
            content: const Text(
                'This removes this prescription from history. It cannot be undone.'),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Cancel')),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: Colors.red.shade700),
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Delete'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed) return;
    try {
      await _service.deletePrescription(prescriptionId);
      if (!mounted) return;
      setState(() => _records.removeWhere((item) => item['id'] == prescriptionId));
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Prescription deleted.')));
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not delete this prescription.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Prescription History'),
        backgroundColor: Colors.white,
        foregroundColor: AppColors.textBlack,
        elevation: 0,
      ),
      body: RefreshIndicator(
        color: AppColors.primaryGreen,
        onRefresh: _load,
        child: _loading
            ? const Center(
                child: CircularProgressIndicator(color: AppColors.primaryGreen))
            : _error != null
                ? ListView(children: [
                    const SizedBox(height: 160),
                    Center(child: Text(_error!)),
                    Center(
                      child: TextButton(onPressed: _load, child: const Text('Try again')),
                    ),
                  ])
                : _records.isEmpty
                    ? ListView(children: const [
                        SizedBox(height: 160),
                        Padding(
                          padding: EdgeInsets.symmetric(horizontal: 32),
                          child: Center(
                            child: Text(
                              'Printed prescriptions will appear here by date and time.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: AppColors.textGrey),
                            ),
                          ),
                        ),
                      ])
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _records.length,
                        itemBuilder: (_, index) => _historyCard(_records[index]),
                      ),
      ),
    );
  }

  Widget _historyCard(Map<String, dynamic> record) {
    final patient = record['patient'] is Map
        ? Map<String, dynamic>.from(record['patient'] as Map)
        : <String, dynamic>{};
    final doctor = record['doctor'] is Map
        ? Map<String, dynamic>.from(record['doctor'] as Map)
        : <String, dynamic>{};
    final medications = record['medications'] is List
        ? record['medications'] as List
        : <dynamic>[];
    final date = DateTime.tryParse(record['printed_at']?.toString() ?? '');
    final dateLabel = date == null
        ? 'Printed prescription'
        : DateFormat('dd MMM yyyy • hh:mm a').format(date.toLocal());

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: Color(0xFFC8E6C9)),
      ),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.fromLTRB(15, 7, 8, 7),
        childrenPadding: const EdgeInsets.fromLTRB(15, 0, 15, 15),
        leading: const CircleAvatar(
          backgroundColor: AppColors.lightGreenBg,
          foregroundColor: AppColors.primaryGreen,
          child: Icon(Icons.description_rounded),
        ),
        title: Text(patient['name']?.toString() ?? 'Patient',
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        subtitle: Text(dateLabel, style: const TextStyle(color: AppColors.textGrey)),
        trailing: IconButton(
          tooltip: 'Delete prescription',
          onPressed: () => _deleteRecord(record),
          color: Colors.red.shade700,
          icon: const Icon(Icons.delete_outline_rounded),
        ),
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Text(dateLabel,
                style: const TextStyle(
                    fontWeight: FontWeight.w800, color: AppColors.primaryGreen)),
          ),
          if ((record['diagnosis']?.toString() ?? '').isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('Diagnosis: ${record['diagnosis']}'),
              ),
            ),
          const Divider(height: 22),
          ...medications.whereType<Map>().map((medicine) {
            final details = [
              medicine['dose'],
              medicine['frequency'],
              medicine['duration'],
              medicine['timing'],
            ]
                .where((value) => value != null && value.toString().trim().isNotEmpty)
                .join(' • ');
            final instruction = medicine['instructions']?.toString().trim() ?? '';
            return Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(
                  '${medicine['name'] ?? ''}${details.isEmpty ? '' : ' — $details'}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                if (instruction.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(instruction,
                        style: const TextStyle(color: AppColors.textGrey)),
                  ),
              ]),
            );
          }),
          const SizedBox(height: 4),
          Text(
            'Dr. ${doctor['name'] ?? ''} • Reg. ${doctor['medical_registration_number'] ?? ''}',
            style: const TextStyle(color: AppColors.textGrey, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
