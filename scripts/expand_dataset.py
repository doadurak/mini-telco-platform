"""
Expand ground_truth.json from 60 to 300 entries.
Adds 240 new entries preserving existing structure and quality.

New phone numbers added for diversity:
  +447700900000  (UK)
  +4917612345678 (DE)
  +33612345678   (FR)
  +81312345678   (JP)

Target distribution (total 300):
  qod_session:       100  (+80)
  qos_profiles:       50  (+40)
  qos_provisioning:   50  (+40)
  location_retrieval: 75  (+60)
  edge_cases:         25  (+20)
"""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
GT_PATH = ROOT / "datasets" / "ground_truth.json"

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
ALL_QOS = [
    "QOS_E", "QOS_S", "QOS_M", "QOS_L",
    "QOS_E_STREAMING", "QOS_GAMING", "QOS_LOW_LATENCY", "QOS_CRITICAL_COMMS",
]

def _dur(minutes: int) -> dict:
    return {"duration_min": minutes * 60, "duration_max": minutes * 60}

def _qod_checks(phone: str, profiles: list[str], duration_min: int, duration_max: int | None = None) -> dict:
    dm = duration_max if duration_max is not None else duration_min
    return {
        "required_fields": ["device", "qosProfile", "duration", "applicationServer"],
        "device.phoneNumber": phone,
        "qosProfile_valid": profiles,
        "duration_min": duration_min,
        "duration_max": dm,
    }

def _prov_checks(phone: str) -> dict:
    return {
        "required_fields": ["device", "qosProfile"],
        "device.phoneNumber": phone,
        "qosProfile_valid": ALL_QOS,
    }

def _loc_checks(phone: str) -> dict:
    return {
        "required_fields": ["device"],
        "device.phoneNumber": phone,
    }

def _profile_checks(phone: str) -> dict:
    return {
        "required_fields": [],
        "device.phoneNumber_if_present": phone,
    }

def qod_en(idx: int, phone: str, intent: str, profiles: list[str],
           dur_min: int, dur_max: int | None, diff: str) -> dict:
    dm = dur_max if dur_max is not None else dur_min
    return {
        "id": f"qod_en_{idx:03d}",
        "intent": intent,
        "language": "en",
        "difficulty": diff,
        "category": "qod_session",
        "source": "synthetic",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": _qod_checks(phone, profiles, dur_min, dm),
    }

def qod_tr(idx: int, phone: str, intent: str, profiles: list[str],
           dur_min: int, dur_max: int | None, diff: str) -> dict:
    dm = dur_max if dur_max is not None else dur_min
    return {
        "id": f"qod_tr_{idx:03d}",
        "intent": intent,
        "language": "tr",
        "difficulty": diff,
        "category": "qod_session",
        "source": "synthetic (Turkish)",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": _qod_checks(phone, profiles, dur_min, dm),
    }

def profile_en(idx: int, phone: str, intent: str, diff: str) -> dict:
    return {
        "id": f"profile_en_{idx:03d}",
        "intent": intent,
        "language": "en",
        "difficulty": diff,
        "category": "qos_profiles",
        "source": "synthetic",
        "expected": {"service_id": "qos-profiles", "operation_id": "retrieveQoSProfiles", "method": "POST"},
        "payload_checks": _profile_checks(phone),
    }

def profile_tr(idx: int, phone: str, intent: str, diff: str) -> dict:
    return {
        "id": f"profile_tr_{idx:03d}",
        "intent": intent,
        "language": "tr",
        "difficulty": diff,
        "category": "qos_profiles",
        "source": "synthetic (Turkish)",
        "expected": {"service_id": "qos-profiles", "operation_id": "retrieveQoSProfiles", "method": "POST"},
        "payload_checks": _profile_checks(phone),
    }

def prov_en(idx: int, phone: str, intent: str, diff: str) -> dict:
    return {
        "id": f"prov_en_{idx:03d}",
        "intent": intent,
        "language": "en",
        "difficulty": diff,
        "category": "qos_provisioning",
        "source": "synthetic",
        "expected": {"service_id": "qos-provisioning", "operation_id": "provisionQoS", "method": "POST"},
        "payload_checks": _prov_checks(phone),
    }

def prov_tr(idx: int, phone: str, intent: str, diff: str) -> dict:
    return {
        "id": f"prov_tr_{idx:03d}",
        "intent": intent,
        "language": "tr",
        "difficulty": diff,
        "category": "qos_provisioning",
        "source": "synthetic (Turkish)",
        "expected": {"service_id": "qos-provisioning", "operation_id": "provisionQoS", "method": "POST"},
        "payload_checks": _prov_checks(phone),
    }

def loc_en(idx: int, phone: str, intent: str, diff: str) -> dict:
    return {
        "id": f"loc_en_{idx:03d}",
        "intent": intent,
        "language": "en",
        "difficulty": diff,
        "category": "location_retrieval",
        "source": "synthetic",
        "expected": {"service_id": "location-retrieval", "operation_id": "retrieveLocation", "method": "POST"},
        "payload_checks": _loc_checks(phone),
    }

def loc_tr(idx: int, phone: str, intent: str, diff: str) -> dict:
    return {
        "id": f"loc_tr_{idx:03d}",
        "intent": intent,
        "language": "tr",
        "difficulty": diff,
        "category": "location_retrieval",
        "source": "synthetic (Turkish)",
        "expected": {"service_id": "location-retrieval", "operation_id": "retrieveLocation", "method": "POST"},
        "payload_checks": _loc_checks(phone),
    }

# ---------------------------------------------------------------------------
# New entries (existing IDs start at 001-010, new ones start at 011)
# ---------------------------------------------------------------------------
NEW_ENTRIES: list[dict] = []

# ============================================================
# QOD SESSION — EN (add 40: IDs 011-050)
# ============================================================
NEW_ENTRIES += [
    # --- Easy (011-022) ---
    qod_en(11, "+447700900000", "Start a QoS session for +447700900000 for 10 minutes", ALL_QOS, 600, 600, "easy"),
    qod_en(12, "+4917612345678", "Create QoD session for device +4917612345678, 25 minutes", ALL_QOS, 1500, 1500, "easy"),
    qod_en(13, "+33612345678", "Boost network quality for +33612345678 for 5 minutes", ALL_QOS, 300, 300, "easy"),
    qod_en(14, "+81312345678", "Apply QoS enhancement to +81312345678 for 30 minutes", ALL_QOS, 1800, 1800, "easy"),
    qod_en(15, "+306912345678", "Set up a streaming QoS session for +306912345678, 20 minutes", ["QOS_E_STREAMING"], 1200, 1200, "easy"),
    qod_en(16, "+905551112233", "Enable gaming QoS for +905551112233 for 45 minutes", ["QOS_GAMING"], 2700, 2700, "easy"),
    qod_en(17, "+34600000000", "Create a small QoS session for +34600000000, 10 minutes", ["QOS_S", "QOS_E", "QOS_M", "QOS_L"], 600, 600, "easy"),
    qod_en(18, "+12025550180", "Give +12025550180 standard QoS boost for half an hour", ["QOS_S", "QOS_E", "QOS_M", "QOS_L"], 1800, 1800, "easy"),
    qod_en(19, "+447700900000", "Open a QoD session for +447700900000, large profile, 15 min", ["QOS_L", "QOS_E"], 900, 900, "easy"),
    qod_en(20, "+4917612345678", "Start streaming quality session for +4917612345678, 1 hour", ["QOS_E_STREAMING", "QOS_E"], 3600, 3600, "easy"),
    qod_en(21, "+33612345678", "Activate QoS low latency for +33612345678, 20 minutes", ["QOS_LOW_LATENCY"], 1200, 1200, "easy"),
    qod_en(22, "+81312345678", "Request QoD session for device +81312345678, 30 min, gaming", ["QOS_GAMING"], 1800, 1800, "easy"),
    # --- Medium (023-036) ---
    qod_en(23, "+447700900000", "My device +447700900000 needs a high quality video call session for 90 minutes", ["QOS_E_STREAMING", "QOS_E", "QOS_M", "QOS_L"], 5400, 5400, "medium"),
    qod_en(24, "+4917612345678", "I'm presenting remotely on +4917612345678 — can you guarantee video quality for 2 hours?", ["QOS_E_STREAMING", "QOS_E", "QOS_M"], 7200, 7200, "medium"),
    qod_en(25, "+33612345678", "The device +33612345678 needs minimum jitter for the next hour for our live broadcast", ["QOS_E_STREAMING", "QOS_LOW_LATENCY"], 3600, 3600, "medium"),
    qod_en(26, "+81312345678", "We're running a VR demo on +81312345678 and need ultra-low latency QoS for 45 min", ["QOS_LOW_LATENCY"], 2700, 2700, "medium"),
    qod_en(27, "+306912345678", "Provide enhanced QoS to +306912345678 for a 40-minute online gaming tournament", ["QOS_GAMING"], 2400, 2400, "medium"),
    qod_en(28, "+905551112233", "Activate a network quality boost on +905551112233 for an important 1-hour meeting", ["QOS_E", "QOS_M", "QOS_L", "QOS_E_STREAMING"], 3600, 3600, "medium"),
    qod_en(29, "+34600000000", "Set up temporary QoS improvement for +34600000000, 35 minutes, medium quality", ["QOS_M", "QOS_E", "QOS_S", "QOS_L"], 2100, 2100, "medium"),
    qod_en(30, "+12025550180", "Enable QoS for drone video transmission from +12025550180, 50 minutes high quality", ["QOS_E_STREAMING", "QOS_E"], 3000, 3000, "medium"),
    qod_en(31, "+447700900000", "Our engineer on +447700900000 needs a reliable connection for remote surgery assistance, 1 hour", ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY"], 3600, 3600, "medium"),
    qod_en(32, "+4917612345678", "Schedule a QoS boost for +4917612345678 to handle the peak traffic during afternoon shift", ALL_QOS, 1, 7200, "medium"),
    qod_en(33, "+33612345678", "Give +33612345678 the low-latency profile — they're participating in a competitive eSports match for 2 hours", ["QOS_LOW_LATENCY", "QOS_GAMING"], 7200, 7200, "medium"),
    qod_en(34, "+81312345678", "Temporarily assign a higher QoS tier to +81312345678 for their telemedicine consultation, 30 min", ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY", "QOS_E"], 1800, 1800, "medium"),
    # --- Hard (037-050) ---
    qod_en(35, "+447700900000", "The device +447700900000 is running a critical infrastructure monitoring agent — assign maximum priority QoS, no time constraint", ["QOS_CRITICAL_COMMS"], 1, 7200, "hard"),
    qod_en(36, "+4917612345678", "For +4917612345678, I need a QoS session but only if emergency conditions apply", ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY"], 1, 7200, "hard"),
    qod_en(37, "+33612345678", "This device +33612345678 might need either streaming or gaming QoS depending on which application activates first — set up a general boost for 60 seconds", ["QOS_E_STREAMING", "QOS_GAMING"], 60, 60, "hard"),
    qod_en(38, "+81312345678", "Apply the highest possible temporary network performance tier to +81312345678 for a 120-second test window", ["QOS_E", "QOS_CRITICAL_COMMS"], 120, 120, "hard"),
    qod_en(39, "+306912345678", "Create a QoD session for +306912345678 — this is for a live TV broadcast but we don't know the exact duration yet, assume max", ALL_QOS, 7200, 7200, "hard"),
    qod_en(40, "+905551112233", "Activate the smallest unit of QoS that still guarantees no packet drop for +905551112233", ["QOS_S", "QOS_E", "QOS_M", "QOS_L", "QOS_CRITICAL_COMMS"], 1, 7200, "hard"),
    qod_en(41, "+34600000000", "The team lead at +34600000000 needs QoS that covers both high-quality video and low latency simultaneously — prioritise whichever is available, 2 hours", ["QOS_LOW_LATENCY", "QOS_E_STREAMING"], 7200, 7200, "hard"),
    qod_en(42, "+12025550180", "Enable enhanced network for +12025550180; it is an autonomous vehicle edge node — latency must be sub-millisecond, session as long as needed", ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY"], 1, 7200, "hard"),
    qod_en(43, "+447700900000", "For device +447700900000 initiate QoD session — service type is unspecified by the requester, infer from context: field hospital equipment", ["QOS_CRITICAL_COMMS"], 1, 7200, "hard"),
    qod_en(44, "+4917612345678", "Start a network quality session for +4917612345678 for the duration of the scheduled system maintenance window", ALL_QOS, 1, 7200, "hard"),
    qod_en(45, "+33612345678", "Our IoT gateway at +33612345678 requires QoS but the use case alternates between streaming and control-plane messaging every 5 min", ALL_QOS, 1, 7200, "hard"),
    qod_en(46, "+81312345678", "Create QoS session for +81312345678; operator policy says no gaming profiles on this SIM — use next best", ["QOS_E", "QOS_M", "QOS_L", "QOS_E_STREAMING", "QOS_LOW_LATENCY"], 1800, 1800, "hard"),
    qod_en(47, "+306912345678", "I want to apply the emergency communications profile to +306912345678 but only for 30 seconds as a failover test", ["QOS_CRITICAL_COMMS"], 30, 30, "hard"),
    qod_en(48, "+905551112233", "Activate a QoD session for +905551112233 — this device is a CCTV relay node; pick the best profile for continuous 4K video upload, 1 hour", ["QOS_E_STREAMING", "QOS_E"], 3600, 3600, "hard"),
    qod_en(49, "+34600000000", "Set up streaming QoS for device +34600000000, just like last time but extend duration by 50%", ["QOS_E_STREAMING", "QOS_E"], 1, 7200, "hard"),
    qod_en(50, "+12025550180", "Provision the minimum viable QoS profile for +12025550180 that allows uninterrupted VoIP for 15 minutes", ["QOS_S", "QOS_M", "QOS_E", "QOS_LOW_LATENCY"], 900, 900, "hard"),
]

# ============================================================
# QOD SESSION — TR (add 40: IDs 011-050)
# ============================================================
NEW_ENTRIES += [
    # --- Easy (011-022) ---
    qod_tr(11, "+447700900000", "+447700900000 için 10 dakikalık QoD oturumu başlat", ALL_QOS, 600, 600, "easy"),
    qod_tr(12, "+4917612345678", "+4917612345678 cihazı için 25 dakika QoD oturumu oluştur", ALL_QOS, 1500, 1500, "easy"),
    qod_tr(13, "+33612345678", "+33612345678 için 5 dakika ağ kalitesini artır", ALL_QOS, 300, 300, "easy"),
    qod_tr(14, "+81312345678", "+81312345678 cihazına 30 dakika QoS iyileştirmesi uygula", ALL_QOS, 1800, 1800, "easy"),
    qod_tr(15, "+306912345678", "+306912345678 için 20 dakika yayın kalitesi oturumu aç", ["QOS_E_STREAMING"], 1200, 1200, "easy"),
    qod_tr(16, "+905551112233", "+905551112233 için 45 dakika oyun QoS'u etkinleştir", ["QOS_GAMING"], 2700, 2700, "easy"),
    qod_tr(17, "+34600000000", "+34600000000 için 10 dakikalık küçük QoS oturumu oluştur", ["QOS_S", "QOS_E", "QOS_M", "QOS_L"], 600, 600, "easy"),
    qod_tr(18, "+12025550180", "+12025550180 için yarım saat standart QoS artışı ver", ["QOS_S", "QOS_E", "QOS_M", "QOS_L"], 1800, 1800, "easy"),
    qod_tr(19, "+447700900000", "+447700900000 için 15 dakika büyük profil QoD oturumu aç", ["QOS_L", "QOS_E"], 900, 900, "easy"),
    qod_tr(20, "+4917612345678", "+4917612345678 için 1 saat yayın kalitesi oturumu başlat", ["QOS_E_STREAMING", "QOS_E"], 3600, 3600, "easy"),
    qod_tr(21, "+33612345678", "+33612345678 için 20 dakika düşük gecikmeli QoS etkinleştir", ["QOS_LOW_LATENCY"], 1200, 1200, "easy"),
    qod_tr(22, "+81312345678", "+81312345678 cihazı için 30 dakika oyun kalitesi QoD oturumu", ["QOS_GAMING"], 1800, 1800, "easy"),
    # --- Medium (023-036) ---
    qod_tr(23, "+447700900000", "+447700900000 cihazım 90 dakika yüksek kaliteli video görüşmesi için QoS oturumuna ihtiyaç duyuyor", ["QOS_E_STREAMING", "QOS_E", "QOS_M", "QOS_L"], 5400, 5400, "medium"),
    qod_tr(24, "+4917612345678", "+4917612345678 üzerinden 2 saatlik uzaktan sunum yapıyorum — video kalitesini garanti eder misin?", ["QOS_E_STREAMING", "QOS_E", "QOS_M"], 7200, 7200, "medium"),
    qod_tr(25, "+33612345678", "+33612345678 cihazı canlı yayın için 1 saat boyunca minimum titreşim gerektiriyor", ["QOS_E_STREAMING", "QOS_LOW_LATENCY"], 3600, 3600, "medium"),
    qod_tr(26, "+81312345678", "+81312345678'de VR demo çalıştırıyoruz, 45 dakika ultra düşük gecikme QoS gerekiyor", ["QOS_LOW_LATENCY"], 2700, 2700, "medium"),
    qod_tr(27, "+306912345678", "+306912345678 için 40 dakikalık çevrimiçi oyun turnuvası süresince artırılmış QoS sağla", ["QOS_GAMING"], 2400, 2400, "medium"),
    qod_tr(28, "+905551112233", "Önemli 1 saatlik toplantı için +905551112233 üzerinde ağ kalitesi artışı etkinleştir", ["QOS_E", "QOS_M", "QOS_L", "QOS_E_STREAMING"], 3600, 3600, "medium"),
    qod_tr(29, "+34600000000", "+34600000000 için 35 dakika orta kalite geçici QoS iyileştirmesi yap", ["QOS_M", "QOS_E", "QOS_S", "QOS_L"], 2100, 2100, "medium"),
    qod_tr(30, "+12025550180", "+12025550180 üzerinden 50 dakika insansız hava aracı video iletimi için yüksek kalite QoS etkinleştir", ["QOS_E_STREAMING", "QOS_E"], 3000, 3000, "medium"),
    qod_tr(31, "+447700900000", "+447700900000'deki mühendisimiz uzaktan cerrahi yardım için güvenilir bağlantıya ihtiyaç duyuyor, 1 saat", ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY"], 3600, 3600, "medium"),
    qod_tr(32, "+4917612345678", "+4917612345678 için öğleden sonra mesai saatlerindeki yoğun trafiği karşılamak amacıyla QoS artışı planla", ALL_QOS, 1, 7200, "medium"),
    qod_tr(33, "+33612345678", "+33612345678 için 2 saatlik profesyonel e-spor maçı süresince düşük gecikme profili ver", ["QOS_LOW_LATENCY", "QOS_GAMING"], 7200, 7200, "medium"),
    qod_tr(34, "+81312345678", "+81312345678 için 30 dakikalık teletıp konsültasyonu süresince geçici olarak daha yüksek QoS katmanı ata", ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY", "QOS_E"], 1800, 1800, "medium"),
    # --- Hard (037-050) ---
    qod_tr(35, "+447700900000", "+447700900000 kritik altyapı izleme ajanı çalıştırıyor — zaman kısıtı olmaksızın maksimum öncelikli QoS ata", ["QOS_CRITICAL_COMMS"], 1, 7200, "hard"),
    qod_tr(36, "+4917612345678", "+4917612345678 için yalnızca acil durum koşulları geçerliyse QoS oturumu aç", ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY"], 1, 7200, "hard"),
    qod_tr(37, "+33612345678", "+33612345678 hangi uygulamanın önce başladığına göre yayın veya oyun QoS'u gerektiriyor — 60 saniyelik genel artış yap", ["QOS_E_STREAMING", "QOS_GAMING"], 60, 60, "hard"),
    qod_tr(38, "+81312345678", "+81312345678 için 120 saniyelik test penceresi boyunca mümkün olan en yüksek ağ performans katmanını uygula", ["QOS_E", "QOS_CRITICAL_COMMS"], 120, 120, "hard"),
    qod_tr(39, "+306912345678", "+306912345678 için canlı TV yayını amacıyla QoD oturumu oluştur — süre belirsiz, maksimum varsay", ALL_QOS, 7200, 7200, "hard"),
    qod_tr(40, "+905551112233", "+905551112233 için paket kaybı garantisi veren en küçük QoS birimini etkinleştir", ["QOS_S", "QOS_E", "QOS_M", "QOS_L", "QOS_CRITICAL_COMMS"], 1, 7200, "hard"),
    qod_tr(41, "+34600000000", "+34600000000 hem yüksek kaliteli video hem düşük gecikme istiyor — mevcut olanı önceliklendir, 2 saat", ["QOS_LOW_LATENCY", "QOS_E_STREAMING"], 7200, 7200, "hard"),
    qod_tr(42, "+12025550180", "+12025550180 otonom araç kenar düğümü — gecikme 1 ms altında olmalı, oturum süresiz", ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY"], 1, 7200, "hard"),
    qod_tr(43, "+447700900000", "+447700900000 için QoD oturumu başlat — talep eden hizmet türü belirtmemiş; bağlamdan çıkar: alan hastanesi ekipmanı", ["QOS_CRITICAL_COMMS"], 1, 7200, "hard"),
    qod_tr(44, "+4917612345678", "+4917612345678 için planlı sistem bakım penceresi süresince ağ kalitesi oturumu başlat", ALL_QOS, 1, 7200, "hard"),
    qod_tr(45, "+33612345678", "+33612345678 IoT ağ geçidi — her 5 dakikada yayın ve kontrol düzlemi mesajlaşması arasında geçiş yapıyor", ALL_QOS, 1, 7200, "hard"),
    qod_tr(46, "+81312345678", "+81312345678 için QoS oturumu aç; operatör politikası bu SIM'de oyun profili yasaklıyor — en iyi alternatifi kullan", ["QOS_E", "QOS_M", "QOS_L", "QOS_E_STREAMING", "QOS_LOW_LATENCY"], 1800, 1800, "hard"),
    qod_tr(47, "+306912345678", "+306912345678 için yalnızca 30 saniyelik yük devretme testi amacıyla acil iletişim profilini uygula", ["QOS_CRITICAL_COMMS"], 30, 30, "hard"),
    qod_tr(48, "+905551112233", "+905551112233 CCTV röle düğümü; kesintisiz 4K video yüklemesi için en iyi profili seç, 1 saat", ["QOS_E_STREAMING", "QOS_E"], 3600, 3600, "hard"),
    qod_tr(49, "+34600000000", "+34600000000 için yayın QoS oturumu aç — süreyi %50 uzat", ["QOS_E_STREAMING", "QOS_E"], 1, 7200, "hard"),
    qod_tr(50, "+12025550180", "+12025550180 için 15 dakika kesintisiz VoIP sağlayan minimum uygulanabilir QoS profilini yükle", ["QOS_S", "QOS_M", "QOS_E", "QOS_LOW_LATENCY"], 900, 900, "hard"),
]

# ============================================================
# QOS PROFILES — EN (add 20: IDs 005-024)
# ============================================================
NEW_ENTRIES += [
    profile_en(5,  "+447700900000",   "Show me all available QoS profiles for +447700900000", "easy"),
    profile_en(6,  "+4917612345678",  "List QoS profiles supported for device +4917612345678", "easy"),
    profile_en(7,  "+33612345678",    "What network quality tiers can I apply to +33612345678?", "easy"),
    profile_en(8,  "+81312345678",    "Retrieve QoS capability list for device +81312345678", "easy"),
    profile_en(9,  "+306912345678",   "Get all QoS options for +306912345678 before starting a session", "medium"),
    profile_en(10, "+905551112233",   "Which QoS profiles are suitable for gaming on +905551112233?", "medium"),
    profile_en(11, "+34600000000",    "Check what performance tiers are available for +34600000000 — we need to pick the right one for our IoT fleet", "medium"),
    profile_en(12, "+12025550180",    "Before provisioning, show me all QoS profiles for +12025550180 with lowest latency options first", "medium"),
    profile_en(13, "+447700900000",   "I want to evaluate the QoS catalogue for +447700900000 to decide if CRITICAL_COMMS is available", "hard"),
    profile_en(14, "+4917612345678",  "Retrieve QoS profiles for +4917612345678 — only show those compatible with real-time media", "hard"),
    profile_en(15, "+33612345678",    "List profiles for +33612345678 — this device will be used for a mission-critical system, so I need to audit what's available", "hard"),
    profile_en(16, "+81312345678",    "Can you tell me all quality tiers available for +81312345678 without activating any session?", "easy"),
    profile_en(17, "+306912345678",   "Enumerate all QoS profiles for +306912345678", "easy"),
    profile_en(18, "+905551112233",   "Show QoS capabilities for +905551112233 including streaming and gaming options", "medium"),
    profile_en(19, "+34600000000",    "What are the currently supported QoS profiles for +34600000000 in this network?", "easy"),
    profile_en(20, "+12025550180",    "Provide the list of available QoS tiers for +12025550180", "easy"),
    profile_en(21, "+447700900000",   "Audit all QoS options for +447700900000 before the SLA negotiation with the customer", "hard"),
    profile_en(22, "+4917612345678",  "Query the available QoS profiles for +4917612345678 to prepare a network capacity report", "medium"),
    profile_en(23, "+33612345678",    "I need to list QoS profiles for +33612345678 — we plan to use the best one for AR/VR traffic", "medium"),
    profile_en(24, "+81312345678",    "Check the QoS menu for +81312345678 — the field engineer needs this info before deployment", "hard"),
]

# ============================================================
# QOS PROFILES — TR (add 20: IDs 005-024)
# ============================================================
NEW_ENTRIES += [
    profile_tr(5,  "+447700900000",   "+447700900000 için mevcut tüm QoS profillerini göster", "easy"),
    profile_tr(6,  "+4917612345678",  "+4917612345678 cihazı için desteklenen QoS profillerini listele", "easy"),
    profile_tr(7,  "+33612345678",    "+33612345678 için hangi ağ kalitesi katmanlarını uygulayabilirim?", "easy"),
    profile_tr(8,  "+81312345678",    "+81312345678 cihazı için QoS kapasitesi listesini al", "easy"),
    profile_tr(9,  "+306912345678",   "Oturum başlatmadan önce +306912345678 için tüm QoS seçeneklerini getir", "medium"),
    profile_tr(10, "+905551112233",   "+905551112233 üzerinde oyun için hangi QoS profilleri uygun?", "medium"),
    profile_tr(11, "+34600000000",    "+34600000000 için mevcut performans katmanlarını kontrol et — IoT filomuz için doğru olanı seçeceğiz", "medium"),
    profile_tr(12, "+12025550180",    "Hazırlamadan önce +12025550180 için en düşük gecikmeli seçenekleri öne çıkararak QoS profillerini göster", "medium"),
    profile_tr(13, "+447700900000",   "+447700900000 için CRITICAL_COMMS'un mevcut olup olmadığını belirlemek amacıyla QoS kataloğunu al", "hard"),
    profile_tr(14, "+4917612345678",  "+4917612345678 için QoS profillerini al — yalnızca gerçek zamanlı medya ile uyumlu olanları göster", "hard"),
    profile_tr(15, "+33612345678",    "+33612345678 için profilleri listele — cihaz kritik sistemde kullanılacak, mevcut olanları denetlemem gerekiyor", "hard"),
    profile_tr(16, "+81312345678",    "+81312345678 için herhangi bir oturum açmadan tüm kalite katmanlarını söyler misin?", "easy"),
    profile_tr(17, "+306912345678",   "+306912345678 için tüm QoS profillerini numaralandır", "easy"),
    profile_tr(18, "+905551112233",   "+905551112233 için yayın ve oyun seçenekleri dahil QoS kapasitelerini göster", "medium"),
    profile_tr(19, "+34600000000",    "Bu ağda +34600000000 için desteklenen QoS profilleri nelerdir?", "easy"),
    profile_tr(20, "+12025550180",    "+12025550180 için mevcut QoS katmanlarının listesini ver", "easy"),
    profile_tr(21, "+447700900000",   "Müşteri ile SLA müzakeresi öncesinde +447700900000 için tüm QoS seçeneklerini denetle", "hard"),
    profile_tr(22, "+4917612345678",  "Ağ kapasitesi raporu hazırlamak için +4917612345678 için mevcut QoS profillerini sorgula", "medium"),
    profile_tr(23, "+33612345678",    "+33612345678 için QoS profillerini listele — AR/VR trafiği için en iyisini kullanacağız", "medium"),
    profile_tr(24, "+81312345678",    "+81312345678 için QoS menüsünü kontrol et — saha mühendisi konuşlandırma öncesinde bu bilgiye ihtiyaç duyuyor", "hard"),
]

# ============================================================
# QOS PROVISIONING — EN (add 20: IDs 005-024)
# ============================================================
NEW_ENTRIES += [
    prov_en(5,  "+447700900000",   "Provision a permanent QoS assignment for +447700900000", "easy"),
    prov_en(6,  "+4917612345678",  "Set up a long-lived QoS configuration for +4917612345678", "easy"),
    prov_en(7,  "+33612345678",    "Assign a persistent QoS profile to device +33612345678", "easy"),
    prov_en(8,  "+81312345678",    "Provision QoS for +81312345678 as a standing configuration", "easy"),
    prov_en(9,  "+306912345678",   "Apply a fixed high-priority QoS assignment to +306912345678 for always-on video feed", "medium"),
    prov_en(10, "+905551112233",   "Configure a permanent low-latency QoS policy for +905551112233 used in factory automation", "medium"),
    prov_en(11, "+34600000000",    "Set up a long-term enhanced QoS for +34600000000 — this device is always streaming to our control centre", "medium"),
    prov_en(12, "+12025550180",    "Provision a persistent network quality assignment for +12025550180 to support ongoing operations", "medium"),
    prov_en(13, "+447700900000",   "I need to permanently assign critical-comms QoS to +447700900000 — it is a first-responder device", "hard"),
    prov_en(14, "+4917612345678",  "Establish a long-lived QoS provisioning for +4917612345678 to guarantee always-on connectivity for our remote sensor", "hard"),
    prov_en(15, "+33612345678",    "Provision a fixed QoS policy for +33612345678 — the device serves as a permanent surveillance camera uplink", "hard"),
    prov_en(16, "+81312345678",    "Apply a standing QoS enhancement to +81312345678 without expiry", "easy"),
    prov_en(17, "+306912345678",   "Permanently configure streaming QoS for device +306912345678", "easy"),
    prov_en(18, "+905551112233",   "Provision a default-on enhanced profile for +905551112233", "medium"),
    prov_en(19, "+34600000000",    "Set up an always-active QoS plan for +34600000000 as part of the managed service agreement", "medium"),
    prov_en(20, "+12025550180",    "I want to provision the gaming QoS profile for +12025550180 as a standing subscription", "easy"),
    prov_en(21, "+447700900000",   "Configure a perpetual low-latency QoS assignment for +447700900000 running industrial robotics", "hard"),
    prov_en(22, "+4917612345678",  "Provision streaming QoS as a baseline service for +4917612345678 — our broadcast van", "medium"),
    prov_en(23, "+33612345678",    "Set up medium-tier QoS provisioning for +33612345678 to underpin regular business traffic", "easy"),
    prov_en(24, "+81312345678",    "Permanently assign the best available QoS to +81312345678 used for remote patient monitoring", "hard"),
]

# ============================================================
# QOS PROVISIONING — TR (add 20: IDs 005-024)
# ============================================================
NEW_ENTRIES += [
    prov_tr(5,  "+447700900000",   "+447700900000 için kalıcı QoS ataması yap", "easy"),
    prov_tr(6,  "+4917612345678",  "+4917612345678 için uzun süreli QoS yapılandırması oluştur", "easy"),
    prov_tr(7,  "+33612345678",    "+33612345678 cihazına kalıcı QoS profili ata", "easy"),
    prov_tr(8,  "+81312345678",    "+81312345678 için sürekli yapılandırma olarak QoS hazırla", "easy"),
    prov_tr(9,  "+306912345678",   "Sürekli video akışı için +306912345678'e sabit yüksek öncelikli QoS ataması uygula", "medium"),
    prov_tr(10, "+905551112233",   "Fabrika otomasyonunda kullanılan +905551112233 için kalıcı düşük gecikmeli QoS politikası yapılandır", "medium"),
    prov_tr(11, "+34600000000",    "+34600000000 kontrol merkezimize sürekli yayın yapıyor — uzun vadeli artırılmış QoS kur", "medium"),
    prov_tr(12, "+12025550180",    "Süregelen operasyonları desteklemek için +12025550180 için kalıcı ağ kalitesi ataması hazırla", "medium"),
    prov_tr(13, "+447700900000",   "+447700900000 birinci müdahale cihazı — kritik iletişim QoS'unu kalıcı olarak ataması gerekiyor", "hard"),
    prov_tr(14, "+4917612345678",  "Uzak sensörümüz için +4917612345678'e her zaman bağlı olmasını garantilemek üzere uzun süreli QoS hazırla", "hard"),
    prov_tr(15, "+33612345678",    "+33612345678 kalıcı gözetim kamerası uplink olarak hizmet veriyor — sabit QoS politikası hazırla", "hard"),
    prov_tr(16, "+81312345678",    "+81312345678 için süresiz QoS geliştirmesi uygula", "easy"),
    prov_tr(17, "+306912345678",   "+306912345678 cihazı için yayın QoS'unu kalıcı olarak yapılandır", "easy"),
    prov_tr(18, "+905551112233",   "+905551112233 için varsayılan olarak açık artırılmış profil hazırla", "medium"),
    prov_tr(19, "+34600000000",    "Yönetilen hizmet sözleşmesi kapsamında +34600000000 için her zaman etkin QoS planı kur", "medium"),
    prov_tr(20, "+12025550180",    "+12025550180 için oyun QoS profilini sürekli abonelik olarak yüklemek istiyorum", "easy"),
    prov_tr(21, "+447700900000",   "Endüstriyel robotik sistemler çalıştıran +447700900000 için sürekli düşük gecikmeli QoS ataması yapılandır", "hard"),
    prov_tr(22, "+4917612345678",  "Yayın aracımız +4917612345678 için temel hizmet olarak yayın QoS'u hazırla", "medium"),
    prov_tr(23, "+33612345678",    "Normal iş trafiğini desteklemek için +33612345678 için orta katman QoS sağlama kur", "easy"),
    prov_tr(24, "+81312345678",    "Uzaktan hasta takibi için kullanılan +81312345678 için en iyi mevcut QoS'u kalıcı olarak ata", "hard"),
]

# ============================================================
# LOCATION RETRIEVAL — EN (add 30: IDs 010-039)
# ============================================================
NEW_ENTRIES += [
    # Easy
    loc_en(10, "+447700900000",   "Where is +447700900000 right now?", "easy"),
    loc_en(11, "+4917612345678",  "Get the current location of device +4917612345678", "easy"),
    loc_en(12, "+33612345678",    "Locate device +33612345678", "easy"),
    loc_en(13, "+81312345678",    "Find the position of +81312345678", "easy"),
    loc_en(14, "+306912345678",   "What is the current location of +306912345678?", "easy"),
    loc_en(15, "+905551112233",   "Retrieve location for +905551112233", "easy"),
    loc_en(16, "+34600000000",    "Tell me where +34600000000 is located", "easy"),
    loc_en(17, "+12025550180",    "Get GPS coordinates for device +12025550180", "easy"),
    loc_en(18, "+447700900000",   "Look up the position of +447700900000 on the network", "easy"),
    loc_en(19, "+4917612345678",  "Show me the location of +4917612345678", "easy"),
    # Medium
    loc_en(20, "+33612345678",    "I need to know where device +33612345678 is so I can dispatch a technician", "medium"),
    loc_en(21, "+81312345678",    "Our field agent on +81312345678 hasn't checked in — find their current location please", "medium"),
    loc_en(22, "+306912345678",   "The vehicle equipped with +306912345678 has gone off route — retrieve its current position", "medium"),
    loc_en(23, "+905551112233",   "Can you locate the device +905551112233 for our emergency response system?", "medium"),
    loc_en(24, "+34600000000",    "We are tracking asset on +34600000000 — fetch latest location data", "medium"),
    loc_en(25, "+12025550180",    "What cell tower area is +12025550180 currently in?", "medium"),
    loc_en(26, "+447700900000",   "Retrieve the geographic position of +447700900000 for our logistics dashboard", "medium"),
    loc_en(27, "+4917612345678",  "Our delivery drone on +4917612345678 needs location check — please retrieve", "medium"),
    loc_en(28, "+33612345678",    "Pinpoint +33612345678 — this is for a parcel tracking integration", "medium"),
    loc_en(29, "+81312345678",    "Fetch the approximate location of device +81312345678 for fleet management", "medium"),
    # Hard
    loc_en(30, "+306912345678",   "The device +306912345678 was last seen near the port — has it moved? Retrieve current location", "hard"),
    loc_en(31, "+905551112233",   "Can you track +905551112233 without alerting the user? Retrieve network location passively", "hard"),
    loc_en(32, "+34600000000",    "I need the location of +34600000000 but the device may be off — get whatever last known position the network has", "hard"),
    loc_en(33, "+12025550180",    "Retrieve position of +12025550180 — it is a moving asset and we need real-time tracking every 30 seconds", "hard"),
    loc_en(34, "+447700900000",   "Where is device +447700900000 based on network signal, not GPS? Use the CAMARA API to retrieve location", "hard"),
    loc_en(35, "+4917612345678",  "Find +4917612345678 — last ping was from a roaming network, what does location-retrieval return?", "hard"),
    loc_en(36, "+33612345678",    "Locate +33612345678 in the context of a missing persons alert — this is time sensitive", "hard"),
    loc_en(37, "+81312345678",    "The device +81312345678 is expected to be in a coverage dead zone — retrieve whatever location data is available", "hard"),
    loc_en(38, "+306912345678",   "Track location of +306912345678 — it's a child-safety device and the parent has authorised location disclosure", "hard"),
    loc_en(39, "+905551112233",   "Retrieve precise location of +905551112233 for autonomous vehicle geofencing verification", "hard"),
]

# ============================================================
# LOCATION RETRIEVAL — TR (add 30: IDs 010-039)
# ============================================================
NEW_ENTRIES += [
    # Easy
    loc_tr(10, "+447700900000",   "+447700900000 şu an nerede?", "easy"),
    loc_tr(11, "+4917612345678",  "+4917612345678 cihazının şu anki konumunu al", "easy"),
    loc_tr(12, "+33612345678",    "+33612345678 cihazını konumlandır", "easy"),
    loc_tr(13, "+81312345678",    "+81312345678'in pozisyonunu bul", "easy"),
    loc_tr(14, "+306912345678",   "+306912345678'in mevcut konumu nedir?", "easy"),
    loc_tr(15, "+905551112233",   "+905551112233 için konumu al", "easy"),
    loc_tr(16, "+34600000000",    "+34600000000'ın nerede olduğunu söyle", "easy"),
    loc_tr(17, "+12025550180",    "+12025550180 cihazı için GPS koordinatlarını al", "easy"),
    loc_tr(18, "+447700900000",   "Ağ üzerinde +447700900000'ın pozisyonunu sorgula", "easy"),
    loc_tr(19, "+4917612345678",  "+4917612345678'in konumunu göster", "easy"),
    # Medium
    loc_tr(20, "+33612345678",    "Teknisyen göndermek için +33612345678 cihazının nerede olduğunu bilmem gerekiyor", "medium"),
    loc_tr(21, "+81312345678",    "+81312345678'deki saha görevlimiz rapor vermedi — şu anki konumunu bul", "medium"),
    loc_tr(22, "+306912345678",   "+306912345678 takılan araç rotadan çıktı — şu anki pozisyonunu al", "medium"),
    loc_tr(23, "+905551112233",   "Acil müdahale sistemimiz için +905551112233 cihazını konumlandırabilir misin?", "medium"),
    loc_tr(24, "+34600000000",    "+34600000000 üzerindeki varlığı izliyoruz — en güncel konum verisini getir", "medium"),
    loc_tr(25, "+12025550180",    "+12025550180 şu anda hangi baz istasyonu alanında?", "medium"),
    loc_tr(26, "+447700900000",   "Lojistik panelimiz için +447700900000'ın coğrafi konumunu al", "medium"),
    loc_tr(27, "+4917612345678",  "+4917612345678'deki teslimat dronemiz için konum kontrolü yap — lütfen al", "medium"),
    loc_tr(28, "+33612345678",    "Kargo takip entegrasyonu için +33612345678'i tespit et", "medium"),
    loc_tr(29, "+81312345678",    "Filo yönetimi için +81312345678 cihazının yaklaşık konumunu getir", "medium"),
    # Hard
    loc_tr(30, "+306912345678",   "+306912345678 en son limanda görüldü — hareket etti mi? Mevcut konumunu al", "hard"),
    loc_tr(31, "+905551112233",   "Kullanıcıyı uyarmadan +905551112233'ü takip edebilir misin? Ağ konumunu pasif olarak al", "hard"),
    loc_tr(32, "+34600000000",    "+34600000000'ın konumuna ihtiyacım var ama cihaz kapalı olabilir — ağın sahip olduğu son bilinen konumu getir", "hard"),
    loc_tr(33, "+12025550180",    "+12025550180'in pozisyonunu al — hareketli bir varlık, her 30 saniyede gerçek zamanlı takip gerekiyor", "hard"),
    loc_tr(34, "+447700900000",   "+447700900000 nerede? GPS değil, ağ sinyali bazlı; konumu almak için CAMARA API kullan", "hard"),
    loc_tr(35, "+4917612345678",  "+4917612345678'i bul — son ping dolaşım ağından geldi, location-retrieval ne döndürüyor?", "hard"),
    loc_tr(36, "+33612345678",    "+33612345678'i kayıp şahıs ihbarı bağlamında konumlandır — zaman kritik", "hard"),
    loc_tr(37, "+81312345678",    "+81312345678 sinyal ölü bölgede olabilir — mevcut konum verisini getir", "hard"),
    loc_tr(38, "+306912345678",   "+306912345678'i izle — çocuk güvenlik cihazı, ebeveyn konum açıklamasına izin verdi", "hard"),
    loc_tr(39, "+905551112233",   "Otonom araç coğrafi sınır doğrulaması için +905551112233'ün hassas konumunu al", "hard"),
]

# ============================================================
# EDGE CASES — EN (add 10: IDs 006-015)
# ============================================================
NEW_ENTRIES += [
    {
        "id": "edge_en_006",
        "intent": "Boost performance for +905551112233 for 30 seconds — it's for a quick QoS test",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — deliberate short-duration edge case",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+905551112233", "qosProfile_valid": ALL_QOS,
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_en_007",
        "intent": "I want to both know the location of +306912345678 AND boost its QoS — handle the location request first",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — multi-intent ambiguity (location wins by instruction)",
        "expected": {"service_id": "location-retrieval", "operation_id": "retrieveLocation", "method": "POST"},
        "payload_checks": {"required_fields": ["device"], "device.phoneNumber": "+306912345678"},
    },
    {
        "id": "edge_en_008",
        "intent": "Set up a network quality session for +447700900000 for the entire working day",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — ambiguous duration (8 h > 7200 s max → clamp to max)",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+447700900000", "qosProfile_valid": ALL_QOS,
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_en_009",
        "intent": "For device +4917612345678, apply whatever makes it faster right now",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — vague intent with no profile or duration specified",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+4917612345678", "qosProfile_valid": ALL_QOS,
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_en_010",
        "intent": "What can I do to permanently improve the connection for +33612345678?",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — permanent vs temporary ambiguity (provisioning wins)",
        "expected": {"service_id": "qos-provisioning", "operation_id": "provisionQoS", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile"],
                           "device.phoneNumber": "+33612345678", "qosProfile_valid": ALL_QOS},
    },
    {
        "id": "edge_en_011",
        "intent": "Tell me where +81312345678 is and also list its available QoS profiles",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — multi-service ambiguity (location-retrieval vs qos-profiles)",
        "expected": {"service_id": "location-retrieval", "operation_id": "retrieveLocation", "method": "POST"},
        "payload_checks": {"required_fields": ["device"], "device.phoneNumber": "+81312345678"},
    },
    {
        "id": "edge_en_012",
        "intent": "Create a QoD session for +12025550180 — this is for emergency use, maximum priority, no time limit",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — unbounded duration edge case + critical profile",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+12025550180", "qosProfile_valid": ["QOS_CRITICAL_COMMS"],
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_en_013",
        "intent": "Give +306912345678 faster internet",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — minimal/colloquial intent with no telco terminology",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+306912345678", "qosProfile_valid": ALL_QOS,
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_en_014",
        "intent": "For +905551112233, activate a QoS profile that reduces latency for 2 hours — but if CRITICAL_COMMS is not available use the next best",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — conditional profile fallback instruction",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+905551112233",
                           "qosProfile_valid": ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY", "QOS_E"],
                           "duration_min": 7200, "duration_max": 7200},
    },
    {
        "id": "edge_en_015",
        "intent": "Provision streaming QoS for +447700900000 forever and also check what profiles exist",
        "language": "en", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic — provisioning + profiles conflict (provisioning selected as primary action)",
        "expected": {"service_id": "qos-provisioning", "operation_id": "provisionQoS", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile"],
                           "device.phoneNumber": "+447700900000",
                           "qosProfile_valid": ["QOS_E_STREAMING", "QOS_E"]},
    },
]

# ============================================================
# EDGE CASES — TR (add 10: IDs 006-015)
# ============================================================
NEW_ENTRIES += [
    {
        "id": "edge_tr_006",
        "intent": "+905551112233 için 30 saniyelik hızlı QoS testi — kısa süre de olsa performans artışı yap",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — deliberate short-duration edge case",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+905551112233", "qosProfile_valid": ALL_QOS,
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_tr_007",
        "intent": "+306912345678'in konumunu hem öğrenmek hem de QoS artışı yapmak istiyorum — önce konumu al",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — multi-intent ambiguity (location wins by instruction)",
        "expected": {"service_id": "location-retrieval", "operation_id": "retrieveLocation", "method": "POST"},
        "payload_checks": {"required_fields": ["device"], "device.phoneNumber": "+306912345678"},
    },
    {
        "id": "edge_tr_008",
        "intent": "+447700900000 için tüm iş günü boyunca ağ kalitesi oturumu aç",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — ambiguous duration (8 h > max → clamp)",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+447700900000", "qosProfile_valid": ALL_QOS,
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_tr_009",
        "intent": "+4917612345678 cihazı için şu anda ne yaparsam daha hızlı olur?",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — vague intent with no profile or duration",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+4917612345678", "qosProfile_valid": ALL_QOS,
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_tr_010",
        "intent": "+33612345678 bağlantısını kalıcı olarak nasıl iyileştirebilirim?",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — permanent vs temporary ambiguity (provisioning wins)",
        "expected": {"service_id": "qos-provisioning", "operation_id": "provisionQoS", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile"],
                           "device.phoneNumber": "+33612345678", "qosProfile_valid": ALL_QOS},
    },
    {
        "id": "edge_tr_011",
        "intent": "+81312345678'in nerede olduğunu söyle ve mevcut QoS profillerini de listele",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — multi-service ambiguity (location wins)",
        "expected": {"service_id": "location-retrieval", "operation_id": "retrieveLocation", "method": "POST"},
        "payload_checks": {"required_fields": ["device"], "device.phoneNumber": "+81312345678"},
    },
    {
        "id": "edge_tr_012",
        "intent": "+12025550180 için QoD oturumu oluştur — acil kullanım, maksimum öncelik, süre sınırı yok",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — unbounded duration + critical profile",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+12025550180", "qosProfile_valid": ["QOS_CRITICAL_COMMS"],
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_tr_013",
        "intent": "+306912345678 interneti daha hızlı olsun",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — minimal colloquial intent",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+306912345678", "qosProfile_valid": ALL_QOS,
                           "duration_min": 1, "duration_max": 7200},
    },
    {
        "id": "edge_tr_014",
        "intent": "+905551112233 için 2 saat gecikmeyi azaltan QoS profili etkinleştir — CRITICAL_COMMS yoksa en iyisini kullan",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — conditional fallback instruction",
        "expected": {"service_id": "qod", "operation_id": "createSession", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile", "duration", "applicationServer"],
                           "device.phoneNumber": "+905551112233",
                           "qosProfile_valid": ["QOS_CRITICAL_COMMS", "QOS_LOW_LATENCY", "QOS_E"],
                           "duration_min": 7200, "duration_max": 7200},
    },
    {
        "id": "edge_tr_015",
        "intent": "+447700900000 için yayın QoS'unu kalıcı olarak yükle ve mevcut profilleri de kontrol et",
        "language": "tr", "difficulty": "hard", "category": "edge_case",
        "source": "synthetic (Turkish) — provisioning + profiles conflict (provisioning selected)",
        "expected": {"service_id": "qos-provisioning", "operation_id": "provisionQoS", "method": "POST"},
        "payload_checks": {"required_fields": ["device", "qosProfile"],
                           "device.phoneNumber": "+447700900000",
                           "qosProfile_valid": ["QOS_E_STREAMING", "QOS_E"]},
    },
]


# ---------------------------------------------------------------------------
# Merge and save
# ---------------------------------------------------------------------------
def main() -> None:
    data = json.loads(GT_PATH.read_text(encoding="utf-8"))
    existing_ids = {e["id"] for e in data["entries"]}

    added = 0
    skipped = 0
    for entry in NEW_ENTRIES:
        if entry["id"] in existing_ids:
            skipped += 1
        else:
            data["entries"].append(entry)
            existing_ids.add(entry["id"])
            added += 1

    # Update meta
    total = len(data["entries"])
    data["_meta"]["total_entries"] = total

    # Recount service distribution
    from collections import Counter
    dist = Counter(e["category"] for e in data["entries"])
    data["_meta"]["service_distribution"] = {
        "qod": dist.get("qod_session", 0),
        "qos-profiles": dist.get("qos_profiles", 0),
        "qos-provisioning": dist.get("qos_provisioning", 0),
        "location-retrieval": dist.get("location_retrieval", 0),
        "edge_cases": dist.get("edge_case", 0),
    }

    # Add new phone numbers note
    data["_meta"]["phone_numbers_note"] = (
        "E.164 numbers from FRONT-research-group test fixtures: "
        "+306912345678 (GR), +905551112233 (TR), +34600000000 (ES), +12025550180 (US), "
        "+447700900000 (UK), +4917612345678 (DE), +33612345678 (FR), +81312345678 (JP)"
    )

    GT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Done. Added {added} entries, skipped {skipped} duplicates.")
    print(f"Total entries: {total}")
    print(f"Distribution: {data['_meta']['service_distribution']}")

    # Verify IDs unique
    ids = [e["id"] for e in data["entries"]]
    assert len(ids) == len(set(ids)), "Duplicate IDs found!"
    print("ID uniqueness check: OK")


if __name__ == "__main__":
    main()
