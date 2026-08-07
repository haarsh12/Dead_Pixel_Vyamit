import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../../core/theme.dart';
import '../../models/shop_details.dart';
import 'models/prescription_draft.dart';
import 'prescription_preview_screen.dart';
import 'services/doctor_prescription_service.dart';

class DoctorVoiceScreen extends StatefulWidget {
  final ShopDetails shopDetails;
  final bool isPrinterConnected;
  final VoidCallback togglePrinter;

  const DoctorVoiceScreen({
    super.key,
    required this.shopDetails,
    required this.isPrinterConnected,
    required this.togglePrinter,
  });

  @override
  State<DoctorVoiceScreen> createState() => _DoctorVoiceScreenState();
}

class _DoctorVoiceScreenState extends State<DoctorVoiceScreen>
    with SingleTickerProviderStateMixin {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final DoctorPrescriptionService _service = DoctorPrescriptionService();
  late final AnimationController _pulseController;
  bool _speechReady = false;
  bool _isListening = false;
  bool _isProcessing = false;
  String _transcript = '';
  String _status = 'Tap the microphone and dictate in clear English.';

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _prepareSpeech();
  }

  Future<void> _prepareSpeech() async {
    final available = await _speech.initialize(
      onStatus: _onSpeechStatus,
      onError: (error) {
        if (!mounted) return;
        setState(() {
          _isListening = false;
          _status = 'Voice recognition error: ${error.errorMsg}';
        });
        _pulseController.stop();
      },
    );
    if (mounted) setState(() => _speechReady = available);
  }

  void _onSpeechStatus(String status) {
    if (!mounted || _isProcessing) return;
    if (status == 'done' || status == 'notListening') {
      final shouldSubmit = _isListening && _transcript.trim().isNotEmpty;
      setState(() => _isListening = false);
      _pulseController.stop();
      if (shouldSubmit) _createDraft();
    }
  }

  Future<void> _toggleListening() async {
    if (_isProcessing) return;
    if (!_speechReady) {
      await _prepareSpeech();
      if (!_speechReady) {
        setState(() =>
            _status = 'Microphone permission is required for voice dictation.');
        return;
      }
    }
    if (_isListening) {
      await _speech.stop();
      return;
    }
    setState(() {
      _transcript = '';
      _status =
          'Listening. Speak the patient and medication instructions in English.';
      _isListening = true;
    });
    _pulseController.repeat(reverse: true);
    await _speech.listen(
      localeId: 'en_IN',
      listenFor: const Duration(seconds: 75),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      onResult: (result) {
        if (!mounted) return;
        setState(() => _transcript = result.recognizedWords);
        if (result.finalResult && result.recognizedWords.trim().isNotEmpty) {
          _speech.stop();
        }
      },
    );
  }

  Future<void> _createDraft() async {
    final transcription = _transcript.trim();
    if (transcription.isEmpty || _isProcessing) return;
    setState(() {
      _isProcessing = true;
      _status = 'Converting the dictation into an editable prescription…';
    });
    try {
      final PrescriptionDraft draft =
          await _service.processVoiceStream(transcription);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PrescriptionPreviewScreen(
            initialDraft: draft,
            shopDetails: widget.shopDetails,
            isPrinterConnected: widget.isPrinterConnected,
            togglePrinter: widget.togglePrinter,
          ),
        ),
      );
      if (mounted) {
        setState(() {
          _transcript = '';
          _status = 'Tap the microphone and dictate the next prescription.';
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _status =
            'Could not create a draft. Review the dictation and try again.');
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  @override
  void dispose() {
    _speech.stop();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const medicalBlue = Color(0xFF1B7A9B);
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF17324A),
        elevation: 0,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Prescription Voice',
                style: TextStyle(fontWeight: FontWeight.w700)),
            Text('Doctor dictation',
                style: TextStyle(fontSize: 12, color: Colors.black54)),
          ],
        ),
        actions: [
          IconButton(
            tooltip: widget.isPrinterConnected
                ? 'Printer connected'
                : 'Connect printer',
            onPressed: widget.togglePrinter,
            icon: Icon(
              Icons.print_rounded,
              color: widget.isPrinterConnected
                  ? AppColors.printerConnected
                  : AppColors.printerDisconnected,
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          const _HealthcareBackground(),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(22, 12, 22, 22),
              child: Column(
                children: [
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF2F8FB),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: const Color(0xFFD7E9F0)),
                    ),
                    child: const Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.health_and_safety_outlined,
                            color: medicalBlue),
                        SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'Dictate patient details, diagnosis, medicine name, dose, frequency, duration, timing and advice. The draft always opens for your review.',
                            style: TextStyle(
                                height: 1.38, color: Color(0xFF355465)),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Spacer(),
                  AnimatedBuilder(
                    animation: _pulseController,
                    builder: (_, child) {
                      final scale = 1 + (_pulseController.value * 0.12);
                      return Transform.scale(scale: scale, child: child);
                    },
                    child: InkWell(
                      onTap: _toggleListening,
                      borderRadius: BorderRadius.circular(100),
                      child: Container(
                        width: 170,
                        height: 170,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _isListening
                              ? const Color(0xFFE9F8FC)
                              : Colors.white,
                          border: Border.all(color: medicalBlue, width: 2),
                          boxShadow: const [
                            BoxShadow(
                                color: Color(0x241B7A9B),
                                blurRadius: 28,
                                spreadRadius: 7),
                          ],
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                                _isListening
                                    ? Icons.graphic_eq_rounded
                                    : Icons.mic_rounded,
                                color: medicalBlue,
                                size: 50),
                            const SizedBox(height: 8),
                            Text(
                              _isListening ? 'Listening' : 'Dictate',
                              style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 17,
                                  color: Color(0xFF17324A)),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Text(_status,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                          color: Color(0xFF506B7A), height: 1.35)),
                  const SizedBox(height: 16),
                  Container(
                    constraints: const BoxConstraints(minHeight: 76),
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.9),
                      border: Border.all(color: const Color(0xFFDCE5E9)),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: _transcript.isEmpty
                        ? const Text(
                            'Your English speech-to-text transcription will appear here.',
                            style: TextStyle(color: Colors.black45))
                        : Text(_transcript,
                            style: const TextStyle(fontSize: 15, height: 1.4)),
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isProcessing || _transcript.trim().isEmpty
                          ? null
                          : _createDraft,
                      icon: _isProcessing
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.description_outlined),
                      label: Text(_isProcessing
                          ? 'Creating draft…'
                          : 'Review prescription draft'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: medicalBlue,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 15),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HealthcareBackground extends StatelessWidget {
  const _HealthcareBackground();

  @override
  Widget build(BuildContext context) {
    const tint = Color(0xFFF0F4F6);
    return IgnorePointer(
      child: Stack(
        children: const [
          Positioned(
              top: 40, left: 20, child: Icon(Icons.add, color: tint, size: 42)),
          Positioned(
              top: 150,
              right: 24,
              child: Icon(Icons.medication_outlined, color: tint, size: 46)),
          Positioned(
              top: 360,
              left: 25,
              child: Icon(Icons.vaccines_outlined, color: tint, size: 42)),
          Positioned(
              bottom: 120,
              right: 20,
              child: Icon(Icons.medical_services_outlined, color: tint, size: 44)),
          Positioned(
              bottom: 28,
              left: 70,
              child: Icon(Icons.add, color: tint, size: 30)),
        ],
      ),
    );
  }
}
