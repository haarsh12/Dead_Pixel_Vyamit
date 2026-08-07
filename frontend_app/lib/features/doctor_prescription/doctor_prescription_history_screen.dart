import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

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
      if (mounted)
        setState(() => _error = 'Unable to load prescription history.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7FAFB),
      appBar: AppBar(
          title: const Text('Prescription History'),
          backgroundColor: Colors.white,
          foregroundColor: const Color(0xFF17324A)),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? ListView(children: [
                    const SizedBox(height: 160),
                    Center(child: Text(_error!)),
                    Center(
                        child: TextButton(
                            onPressed: _load, child: const Text('Try again')))
                  ])
                : _records.isEmpty
                    ? ListView(children: const [
                        SizedBox(height: 160),
                        Center(
                            child: Text(
                                'Printed prescriptions will appear here by date and time.'))
                      ])
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _records.length,
                        itemBuilder: (_, index) =>
                            _historyCard(_records[index]),
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
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.print_rounded, size: 18, color: Color(0xFF1B7A9B)),
            const SizedBox(width: 7),
            Expanded(
                child: Text(
                    date == null
                        ? 'Printed prescription'
                        : DateFormat('dd MMM yyyy • hh:mm a')
                            .format(date.toLocal()),
                    style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF1B7A9B)))),
          ]),
          const SizedBox(height: 9),
          Text(patient['name']?.toString() ?? 'Patient',
              style:
                  const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          if ((record['diagnosis']?.toString() ?? '').isNotEmpty)
            Padding(
                padding: const EdgeInsets.only(top: 3),
                child: Text('Diagnosis: ${record['diagnosis']}')),
          const Divider(height: 20),
          ...medications.whereType<Map>().map((medicine) {
            final details = [
              medicine['dose'],
              medicine['frequency'],
              medicine['duration'],
              medicine['timing']
            ]
                .where((value) =>
                    value != null && value.toString().trim().isNotEmpty)
                .join(' • ');
            return Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                  '• ${medicine['name'] ?? ''}${details.isEmpty ? '' : ' — $details'}'),
            );
          }),
          const SizedBox(height: 6),
          Text(
              'Dr. ${doctor['name'] ?? ''}  •  Reg. ${doctor['medical_registration_number'] ?? ''}',
              style: const TextStyle(color: Colors.black54, fontSize: 12)),
        ]),
      ),
    );
  }
}
