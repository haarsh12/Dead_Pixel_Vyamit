import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'services/doctor_prescription_service.dart';

class DoctorPatientListScreen extends StatefulWidget {
  const DoctorPatientListScreen({super.key});

  @override
  State<DoctorPatientListScreen> createState() =>
      _DoctorPatientListScreenState();
}

class _DoctorPatientListScreenState extends State<DoctorPatientListScreen> {
  final _service = DoctorPrescriptionService();
  final _search = TextEditingController();
  List<Map<String, dynamic>> _patients = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final patients = await _service.patients(query: _search.text.trim());
      if (mounted) setState(() => _patients = patients);
    } catch (_) {
      if (mounted) setState(() => _error = 'Unable to load the patient list.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final patient in _patients) {
      final name = patient['name']?.toString().trim() ?? '';
      final letter = name.isEmpty ? '#' : name[0].toUpperCase();
      groups.putIfAbsent(letter, () => []).add(patient);
    }
    return Scaffold(
      backgroundColor: const Color(0xFFF7FAFB),
      appBar: AppBar(
          title: const Text('Patients'),
          backgroundColor: Colors.white,
          foregroundColor: const Color(0xFF17324A)),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextField(
              controller: _search,
              onChanged: (_) => _load(),
              decoration: InputDecoration(
                hintText: 'Search patient by name',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _search.text.isEmpty
                    ? null
                    : IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _search.clear();
                          _load();
                        },
                      ),
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 14),
            if (_loading)
              const Padding(
                  padding: EdgeInsets.all(36),
                  child: Center(child: CircularProgressIndicator()))
            else if (_error != null)
              _emptyState(Icons.cloud_off_outlined, _error!, action: _load)
            else if (_patients.isEmpty)
              _emptyState(Icons.people_outline,
                  'No saved patients yet. Patients are added only when you approve it after printing.')
            else
              ...groups.entries.expand((entry) => [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(4, 12, 4, 7),
                      child: Text(entry.key,
                          style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF1B7A9B))),
                    ),
                    ...entry.value.map((patient) => _patientTile(patient)),
                  ]),
          ],
        ),
      ),
    );
  }

  Widget _patientTile(Map<String, dynamic> patient) {
    final age = patient['age'];
    final gender = patient['gender']?.toString() ?? '';
    final subtitle = [
      if (age != null) '$age yrs',
      if (gender.isNotEmpty) gender
    ].join(' • ');
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: 0,
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: const Color(0xFFE3F2F7),
          child: Text((patient['name']?.toString().isNotEmpty ?? false)
              ? patient['name'].toString()[0].toUpperCase()
              : '?'),
        ),
        title: Text(patient['name']?.toString() ?? '',
            style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text(subtitle.isEmpty ? 'Patient details' : subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
              builder: (_) => DoctorPatientPrescriptionsScreen(
                  patientId: patient['id'] as int)),
        ),
      ),
    );
  }

  Widget _emptyState(IconData icon, String message, {VoidCallback? action}) =>
      Padding(
        padding: const EdgeInsets.only(top: 80),
        child: Column(children: [
          Icon(icon, size: 52, color: Colors.blueGrey.shade300),
          const SizedBox(height: 14),
          Text(message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.black54, height: 1.4)),
          if (action != null)
            TextButton(onPressed: action, child: const Text('Try again')),
        ]),
      );
}

class DoctorPatientPrescriptionsScreen extends StatefulWidget {
  final int patientId;
  const DoctorPatientPrescriptionsScreen({super.key, required this.patientId});

  @override
  State<DoctorPatientPrescriptionsScreen> createState() =>
      _DoctorPatientPrescriptionsScreenState();
}

class _DoctorPatientPrescriptionsScreenState
    extends State<DoctorPatientPrescriptionsScreen> {
  final _service = DoctorPrescriptionService();
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await _service.patientPrescriptions(widget.patientId);
      if (mounted) setState(() => _data = data);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final patient = _data?['patient'] is Map
        ? Map<String, dynamic>.from(_data!['patient'] as Map)
        : <String, dynamic>{};
    final records = _data?['prescriptions'] is List
        ? (_data!['prescriptions'] as List)
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList()
        : <Map<String, dynamic>>[];
    return Scaffold(
      backgroundColor: const Color(0xFFF7FAFB),
      appBar: AppBar(
          title: Text(patient['name']?.toString() ?? 'Patient prescriptions'),
          backgroundColor: Colors.white,
          foregroundColor: const Color(0xFF17324A)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (patient.isNotEmpty) _patientHeader(patient),
                const SizedBox(height: 12),
                const Text('Prescription history',
                    style:
                        TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                if (records.isEmpty)
                  const Padding(
                      padding: EdgeInsets.all(28),
                      child: Center(
                          child: Text(
                              'No printed prescriptions for this patient yet.')))
                else
                  ...records.map(_recordCard),
              ],
            ),
    );
  }

  Widget _patientHeader(Map<String, dynamic> patient) => Card(
        elevation: 0,
        color: const Color(0xFFEAF7FB),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Text(
              [
                patient['name']?.toString() ?? '',
                if (patient['age'] != null) '${patient['age']} yrs',
                if ((patient['gender']?.toString() ?? '').isNotEmpty)
                  patient['gender'].toString(),
              ].join(' • '),
              style: const TextStyle(fontWeight: FontWeight.w700)),
        ),
      );

  Widget _recordCard(Map<String, dynamic> record) {
    final medications = record['medications'] is List
        ? record['medications'] as List
        : <dynamic>[];
    final date = DateTime.tryParse(record['printed_at']?.toString() ?? '');
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
              date == null
                  ? 'Printed prescription'
                  : DateFormat('dd MMM yyyy • hh:mm a').format(date.toLocal()),
              style: const TextStyle(
                  fontWeight: FontWeight.w800, color: Color(0xFF1B7A9B))),
          if ((record['diagnosis']?.toString() ?? '').isNotEmpty)
            Padding(
                padding: const EdgeInsets.only(top: 5),
                child: Text('Diagnosis: ${record['diagnosis']}')),
          const SizedBox(height: 5),
          ...medications.whereType<Map>().map((medicine) =>
              Text('• ${medicine['name'] ?? ''} ${medicine['dose'] ?? ''}')),
        ]),
      ),
    );
  }
}
