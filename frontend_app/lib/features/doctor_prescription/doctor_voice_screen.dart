import 'dart:async';

import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../../core/theme.dart';
import '../../models/shop_details.dart';
import 'models/prescription_draft.dart';
import 'prescription_preview_screen.dart';
import 'services/doctor_prescription_service.dart';

/// The doctor voice surface intentionally follows the main voice-page
/// interaction: one tap starts a live session and the next tap closes it.
/// Unlike retail voice, a completed utterance opens an editable prescription
/// rather than starting a spoken back-and-forth conversation.
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

  Timer? _silenceTimer;
  Timer? _restartTimer;
  bool _speechReady = false;
  bool _isSessionActive = false;
  bool _isListening = false;
  bool _isProcessing = false;
  String _sessionState = 'IDLE';
  String _transcript = '';
  double _audioLevel = 0;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 950),
      lowerBound: .82,
      upperBound: 1.18,
    );
  }

  Future<void> _toggleSession() async {
    if (_isProcessing) return;
    if (_isSessionActive) {
      await _finishSession();
    } else {
      await _startSession();
    }
  }

  Future<void> _startSession() async {
    final ready = await _speech.initialize(
      onStatus: _onSpeechStatus,
      onError: _onSpeechError,
    );
    if (!mounted) return;
    if (!ready) {
      setState(() => _sessionState = 'MICROPHONE PERMISSION NEEDED');
      return;
    }
    setState(() {
      _speechReady = true;
      _isSessionActive = true;
      _isListening = true;
      _sessionState = 'LISTENING';
      _transcript = '';
      _audioLevel = .25;
    });
    _pulseController.repeat(reverse: true);
    await _startListening();
  }

  Future<void> _startListening() async {
    if (!_speechReady || !_isSessionActive || _isProcessing ||
        _speech.isListening) {
      return;
    }
    try {
      await _speech.listen(
        localeId: 'en_IN',
        listenMode: stt.ListenMode.dictation,
        listenFor: const Duration(minutes: 5),
        pauseFor: const Duration(seconds: 8),
        partialResults: true,
        cancelOnError: false,
        onResult: (result) {
          if (!mounted || !_isSessionActive) return;
          final words = result.recognizedWords.trim();
          if (words.isEmpty) return;
          setState(() {
            _transcript = words;
            _audioLevel = .75;
          });
          _silenceTimer?.cancel();
          // A brief natural pause submits the dictated prescription, just as
          // the main voice screen dispatches its utterance after silence.
          _silenceTimer = Timer(const Duration(milliseconds: 1800), () {
            if (_isSessionActive && !_isProcessing && _transcript.isNotEmpty) {
              _finishSession(submit: true);
            }
          });
          if (result.finalResult && words.isNotEmpty) {
            _finishSession(submit: true);
          }
        },
      );
    } catch (_) {
      _restartListening();
    }
  }

  void _onSpeechStatus(String status) {
    if (!_isSessionActive || _isProcessing || !mounted) return;
    if (status == 'done' || status == 'notListening') {
      _restartListening();
    }
  }

  void _onSpeechError(stt.SpeechRecognitionError error) {
    if (!mounted) return;
    if (error.errorMsg.toLowerCase().contains('permission')) {
      _stopSession(showIdle: false);
      setState(() => _sessionState = 'MICROPHONE PERMISSION NEEDED');
      return;
    }
    if (_isSessionActive && !_isProcessing) _restartListening();
  }

  void _restartListening() {
    _restartTimer?.cancel();
    _restartTimer = Timer(const Duration(milliseconds: 450), () {
      if (_isSessionActive && !_isProcessing && mounted) _startListening();
    });
  }

  Future<void> _finishSession({bool submit = true}) async {
    if (!_isSessionActive && !_isProcessing) return;
    final transcription = _transcript.trim();
    await _stopSession(showIdle: !submit || transcription.isEmpty);
    if (submit && transcription.isNotEmpty) await _createDraft(transcription);
  }

  Future<void> _stopSession({required bool showIdle}) async {
    _silenceTimer?.cancel();
    _restartTimer?.cancel();
    await _speech.stop();
    _pulseController.stop();
    if (!mounted) return;
    setState(() {
      _isSessionActive = false;
      _isListening = false;
      _audioLevel = 0;
      if (showIdle) _sessionState = 'TAP TO START';
    });
  }

  Future<void> _createDraft(String transcription) async {
    if (_isProcessing) return;
    setState(() {
      _isProcessing = true;
      _sessionState = 'FORMATTING PRESCRIPTION';
    });
    try {
      final draft = await _service.processVoiceStream(transcription);
      if (!mounted) return;
      await _openPreview(draft);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Could not format the dictation. You can still use Manual mode.'),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
          _sessionState = 'TAP TO START';
          _transcript = '';
        });
      }
    }
  }

  Future<void> _openPreview(PrescriptionDraft draft) async {
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
  }

  Future<void> _openManualMode() async {
    await _stopSession(showIdle: true);
    await _openPreview(PrescriptionDraft());
  }

  Future<void> _clearAll() async {
    await _stopSession(showIdle: true);
    if (!mounted) return;
    setState(() => _transcript = '');
  }

  Color get _activeColor => _isProcessing
      ? Colors.teal
      : _isSessionActive
          ? AppColors.primaryGreen
          : Colors.grey;

  @override
  void dispose() {
    _silenceTimer?.cancel();
    _restartTimer?.cancel();
    _speech.stop();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final active = _isSessionActive || _isProcessing;
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        foregroundColor: AppColors.textBlack,
        elevation: 0,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Prescription Voice', style: TextStyle(fontWeight: FontWeight.w800)),
            Text('Speak naturally in English or Hinglish',
                style: TextStyle(fontSize: 12, color: AppColors.textGrey)),
          ],
        ),
        actions: [
          IconButton(
            tooltip: widget.isPrinterConnected ? 'Printer connected' : 'Connect printer',
            onPressed: widget.togglePrinter,
            icon: Icon(
              Icons.print_rounded,
              color: widget.isPrinterConnected
                  ? AppColors.printerConnected
                  : AppColors.printerDisconnected,
            ),
          ),
          IconButton(
            tooltip: 'Clear voice session',
            onPressed: _clearAll,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
          child: Column(
            children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.lightGreenBg,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFC8E6C9)),
                ),
                child: const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.health_and_safety_rounded,
                        color: AppColors.primaryGreen),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Dictate patient details, diagnosis, medicine, dose, frequency, duration and food instructions. A complete editable preview always opens before printing.',
                        style: TextStyle(height: 1.35, color: Color(0xFF28512B)),
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              Stack(
                alignment: Alignment.center,
                children: [
                  if (active) ...[
                    AnimatedBuilder(
                      animation: _pulseController,
                      builder: (_, __) => Container(
                        width: 190 + (_audioLevel * 25),
                        height: 190 + (_audioLevel * 25),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: _activeColor.withValues(alpha: .18),
                            width: 2,
                          ),
                        ),
                      ),
                    ),
                    Container(
                      width: 166 + (_audioLevel * 16),
                      height: 166 + (_audioLevel * 16),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: _activeColor.withValues(alpha: .28),
                          width: 2,
                        ),
                      ),
                    ),
                  ],
                  AnimatedScale(
                    duration: const Duration(milliseconds: 120),
                    scale: active ? 1 + (_audioLevel * .10) : 1,
                    child: InkWell(
                      onTap: _toggleSession,
                      customBorder: const CircleBorder(),
                      child: Ink(
                        width: 142,
                        height: 142,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: active
                              ? LinearGradient(
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                  colors: _isProcessing
                                      ? [Colors.teal.shade700, Colors.teal.shade400]
                                      : [Colors.green.shade800, Colors.green.shade500],
                                )
                              : null,
                          color: active ? null : Colors.white,
                          border: Border.all(
                            color: active ? Colors.transparent : const Color(0xFFA5D6A7),
                            width: 2,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: _activeColor.withValues(alpha: active ? .40 : .16),
                              blurRadius: active ? 30 : 14,
                              spreadRadius: active ? 3 : 1,
                            ),
                          ],
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              _isProcessing
                                  ? Icons.auto_awesome_rounded
                                  : _isSessionActive
                                      ? Icons.graphic_eq_rounded
                                      : Icons.mic_rounded,
                              color: active ? Colors.white : AppColors.primaryGreen,
                              size: 52,
                            ),
                            const SizedBox(height: 7),
                            Text(
                              _isProcessing
                                  ? 'Creating'
                                  : _isSessionActive
                                      ? 'Tap to stop'
                                      : 'Tap to speak',
                              style: TextStyle(
                                color: active ? Colors.white : AppColors.primaryGreen,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 26),
              _statusBadge(),
              const SizedBox(height: 12),
              Text(
                _isSessionActive
                    ? 'Tap the voice circle again when you are finished.'
                    : 'It also creates the draft automatically after you pause.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.textGrey),
              ),
              const SizedBox(height: 14),
              Container(
                constraints: const BoxConstraints(minHeight: 86),
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  border: Border.all(color: const Color(0xFFC8E6C9)),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Text(
                  _transcript.isEmpty
                      ? 'Your live transcription will appear here.'
                      : _transcript,
                  style: TextStyle(
                    color: _transcript.isEmpty ? Colors.black45 : AppColors.textBlack,
                    height: 1.35,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _isProcessing ? null : _clearAll,
                      icon: const Icon(Icons.clear_all_rounded),
                      label: const Text('Clear all'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.primaryGreen,
                        side: const BorderSide(color: Color(0xFF81C784)),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: _isProcessing ? null : _openManualMode,
                      icon: const Icon(Icons.edit_note_rounded),
                      label: const Text('Manual mode'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primaryGreen,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _statusBadge() => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: _activeColor.withValues(alpha: .10),
          borderRadius: BorderRadius.circular(99),
          border: Border.all(color: _activeColor.withValues(alpha: .25)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: _activeColor, shape: BoxShape.circle),
          ),
          const SizedBox(width: 8),
          Text(
            _sessionState,
            style: TextStyle(color: _activeColor.shade700, fontWeight: FontWeight.w800, fontSize: 12),
          ),
        ]),
      );
}
