"""Clinical transcription structuring for Doctor Prescription mode.

This service deliberately differs from retail voice billing: it never uses
inventory, pricing, or sales context, and it must not diagnose, recommend, or
invent medicines.  It only turns the doctor's dictated words into an editable
English prescription draft.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List


logger = logging.getLogger(__name__)

_MAX_MEDICATIONS = 20
_MEDICATION_FIELDS = (
    "name",
    "dose",
    "frequency",
    "duration",
    "timing",
    "route",
    "instructions",
)


class DoctorPrescriptionVoiceService:
    """Turn a spoken doctor instruction into a conservative draft object."""

    def __init__(self) -> None:
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self._client = None
        self._types = None

    def _get_client(self) -> bool:
        if self._client is not None:
            return True
        if not self._api_key:
            return False
        try:
            from google import genai
            from google.genai import types

            self._client = genai.Client(api_key=self._api_key)
            self._types = types
            return True
        except Exception as exc:
            logger.warning("Doctor prescription model unavailable: %s", type(exc).__name__)
            return False

    @staticmethod
    def _text(value: Any, maximum: int) -> str:
        return str(value or "").strip()[:maximum]

    def _prompt(self, transcription: str) -> str:
        return f'''You are a clinical dictation formatter for a licensed doctor.

The doctor said: {json.dumps(transcription, ensure_ascii=False)}

Return JSON only with exactly this shape:
{{
  "patient": {{"name":"", "age":null, "gender":"", "phone":""}},
  "diagnosis":"",
  "medications": [{{
    "name":"", "dose":"", "frequency":"", "duration":"",
    "timing":"", "route":"Oral", "instructions":""
  }}],
  "additional_notes":"",
  "english_transcript":""
}}

Rules:
1. This is transcription formatting, not clinical decision support. Never diagnose, recommend, add, substitute, or infer a medicine, dose, frequency, duration, or instruction.
2. Include only details explicitly dictated by the doctor. Use an empty string or null when a field was not spoken.
3. Write every output field in clear English and preserve the dictated meaning. Translate a spoken Hindi/Hinglish instruction into clear English only when the wording is unambiguous.
4. Keep each medicine separate. "timing" should say, for example, "After food", "Before breakfast", or be empty if not stated.
5. Do not include patient data that was not dictated. Do not return markdown or extra keys.'''

    def _parse_with_gemini(self, transcription: str) -> Dict[str, Any] | None:
        if not self._get_client():
            return None
        for model in ("gemini-2.5-flash-lite", "gemini-2.5-flash"):
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=self._prompt(transcription),
                    config=self._types.GenerateContentConfig(
                        temperature=0,
                        max_output_tokens=2048,
                        response_mime_type="application/json",
                    ),
                )
                return json.loads(response.text)
            except Exception as exc:
                logger.info("Doctor transcription model %s failed: %s", model, type(exc).__name__)
        return None

    @staticmethod
    def _fallback_parse(transcription: str) -> Dict[str, Any]:
        """Best-effort offline extraction without inventing medical facts."""
        text = transcription.strip()
        patient = {"name": "", "age": None, "gender": "", "phone": ""}
        name_match = re.search(r"(?:patient(?:\s+name)?\s*(?:is|:)?\s*)([A-Za-z][A-Za-z .'-]{1,80})", text, re.I)
        if name_match:
            patient["name"] = name_match.group(1).strip(" ,.")
        age_match = re.search(r"\b(?:age\s*)?(\d{1,3})\s*(?:years?|yrs?)\b", text, re.I)
        if age_match:
            age = int(age_match.group(1))
            patient["age"] = age if age <= 130 else None
        gender_match = re.search(r"\b(male|female|other)\b", text, re.I)
        if gender_match:
            patient["gender"] = gender_match.group(1).title()
        phone_match = re.search(r"\b(?:phone|mobile)\s*(?:number)?\s*(?:is|:)?\s*(\+?\d[\d -]{8,18})", text, re.I)
        if phone_match:
            patient["phone"] = re.sub(r"\s+", "", phone_match.group(1))[:20]

        diagnosis = ""
        diagnosis_match = re.search(r"\b(?:diagnosis|diagnosed with|for)\s*[:\-]?\s*([^,.;]+)", text, re.I)
        if diagnosis_match:
            diagnosis = diagnosis_match.group(1).strip()[:500]

        medications: List[Dict[str, str]] = []
        medicine_match = re.search(
            r"\b(?:prescribe|prescribed|give|take)\s+([A-Za-z][A-Za-z0-9 .-]{1,80}?)(?:\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|tablet(?:s)?|capsule(?:s)?)))?(?=\s*(?:,|for\b|twice\b|once\b|three\b|after\b|before\b|$))",
            text,
            re.I,
        )
        if medicine_match:
            frequency = ""
            frequency_match = re.search(r"\b(once daily|twice daily|three times daily|every \d+ hours?)\b", text, re.I)
            if frequency_match:
                frequency = frequency_match.group(1).title()
            duration = ""
            duration_match = re.search(r"\bfor\s+(\d+\s+(?:day|days|week|weeks|month|months))\b", text, re.I)
            if duration_match:
                duration = duration_match.group(1)
            timing = ""
            timing_match = re.search(r"\b(before|after)\s+(?:food|meal|breakfast|lunch|dinner)\b", text, re.I)
            if timing_match:
                timing = timing_match.group(0).title()
            medications.append(
                {
                    "name": medicine_match.group(1).strip(" ,.")[:120],
                    "dose": (medicine_match.group(2) or "").strip()[:60],
                    "frequency": frequency,
                    "duration": duration,
                    "timing": timing,
                    "route": "",
                    "instructions": "",
                }
            )
        return {
            "patient": patient,
            "diagnosis": diagnosis,
            "medications": medications,
            "additional_notes": "",
            "english_transcript": text,
        }

    def _normalise(self, result: Any, transcription: str) -> Dict[str, Any]:
        result = result if isinstance(result, dict) else {}
        patient_source = result.get("patient") if isinstance(result.get("patient"), dict) else {}
        age_value = patient_source.get("age")
        try:
            age = int(age_value) if age_value is not None and str(age_value).strip() else None
        except (TypeError, ValueError):
            age = None
        if age is not None and not 0 <= age <= 130:
            age = None

        medications: List[Dict[str, str]] = []
        source_medicines = result.get("medications") if isinstance(result.get("medications"), list) else []
        for source in source_medicines[:_MAX_MEDICATIONS]:
            if not isinstance(source, dict):
                continue
            medicine = {field: self._text(source.get(field), 400 if field == "instructions" else 120) for field in _MEDICATION_FIELDS}
            if medicine["name"]:
                medications.append(medicine)

        return {
            "patient": {
                "name": self._text(patient_source.get("name"), 120),
                "age": age,
                "gender": self._text(patient_source.get("gender"), 30),
                "phone": self._text(patient_source.get("phone"), 20),
            },
            "diagnosis": self._text(result.get("diagnosis"), 500),
            "medications": medications,
            "additional_notes": self._text(result.get("additional_notes"), 1500),
            "english_transcript": self._text(result.get("english_transcript") or transcription, 2000),
        }

    def process(self, transcription: str) -> Dict[str, Any]:
        """Return an editable draft.  Never retain a raw voice transcript."""
        result = self._parse_with_gemini(transcription)
        draft = self._normalise(result or self._fallback_parse(transcription), transcription)
        logger.info("Doctor prescription transcription processed medication_count=%s", len(draft["medications"]))
        return {
            "type": "PRESCRIPTION_DRAFT",
            "draft": draft,
            "message": "Prescription draft ready for clinical review.",
        }


doctor_prescription_voice_service = DoctorPrescriptionVoiceService()
