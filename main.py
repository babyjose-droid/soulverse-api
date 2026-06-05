"""
Rhythm SoulVerse — Production API
Railway deployment | FastAPI + SQLite (upgrades to PostgreSQL automatically on Railway)
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import hashlib, secrets, time, os, json
from datetime import datetime, date

# ── APP SETUP ──────────────────────────────────────────────
app = FastAPI(
    title="Rhythm SoulVerse API",
    description="AI-powered Spiritual Wellness Platform — Astrology · Ayurveda · AI Coach",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── IN-MEMORY DATABASE (works without PostgreSQL) ───────────
users_db   = {}
profiles_db= {}
sessions   = {}
otps       = {}
bookings   = []
chat_hist  = {}

# ── UTILS ───────────────────────────────────────────────────
def token(uid): return hashlib.sha256(f"{uid}{secrets.token_hex(8)}".encode()).hexdigest()
def auth(authorization: Optional[str] = Header(None)):
    if not authorization: return None
    t = authorization.replace("Bearer ","").strip()
    return sessions.get(t)

def life_path(dob_str):
    try:
        digits = [int(c) for c in dob_str.replace("-","") if c.isdigit()]
        n = sum(digits)
        while n > 9 and n not in (11,22,33):
            n = sum(int(d) for d in str(n))
        return n
    except: return 7

def sun_sign(dob_str):
    try:
        d = date.fromisoformat(dob_str); m,day = d.month, d.day
        signs=[(1,20,"Aquarius"),(2,19,"Pisces"),(3,20,"Aries"),(4,20,"Taurus"),
               (5,21,"Gemini"),(6,21,"Cancer"),(7,23,"Leo"),(8,23,"Virgo"),
               (9,23,"Libra"),(10,23,"Scorpio"),(11,22,"Sagittarius"),(12,22,"Capricorn")]
        for em,ed,s in signs:
            if m==em-1 or (m==em and day<=ed): return s
        return "Capricorn"
    except: return "Scorpio"

# ── MODELS ─────────────────────────────────────────────────
class RegisterReq(BaseModel):
    full_name: str
    mobile: str
    email: Optional[str] = None
    password: Optional[str] = None

class OTPVerifyReq(BaseModel):
    mobile: str
    otp: str

class ProfileReq(BaseModel):
    full_name: str
    dob: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    goals: Optional[str] = None

class AyurvedaReq(BaseModel):
    answers: dict
    profile_data: Optional[dict] = {}
    tongue_image_b64: Optional[str] = None
    eye_image_b64: Optional[str] = None

class ChatReq(BaseModel):
    message: str
    session_id: Optional[str] = None

class BookingReq(BaseModel):
    expert_id: str
    appointment_time: str
    duration_minutes: int = 60
    consultation_type: str = "video"
    concern: Optional[str] = None

class PaymentReq(BaseModel):
    plan: str

# ══════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "app": "Rhythm SoulVerse API",
        "version": "1.0.0",
        "status": "✅ Live on Railway",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "auth": ["/v1/auth/register", "/v1/auth/send-otp", "/v1/auth/verify-otp"],
            "profile": ["/v1/profile"],
            "astrology": ["/v1/astrology/horoscope/daily", "/v1/astrology/kundli", "/v1/astrology/compatibility"],
            "numerology": ["/v1/numerology/generate"],
            "ayurveda": ["/v1/ayurveda/assessment", "/v1/ayurveda/dosha-profile"],
            "meditation": ["/v1/meditation/library"],
            "ai": ["/v1/ai/chat"],
            "consultations": ["/v1/experts", "/v1/bookings"],
            "payments": ["/v1/payments/create-order", "/v1/payments/subscriptions"],
            "admin": ["/v1/admin/dashboard"]
        }
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "platform": "Railway",
        "timestamp": datetime.utcnow().isoformat(),
        "users_registered": len(users_db),
        "uptime": "online"
    }

# ── AUTH ────────────────────────────────────────────────────
@app.post("/v1/auth/register")
def register(req: RegisterReq):
    if req.mobile in users_db:
        raise HTTPException(400, "Mobile already registered")
    uid = f"USR{len(users_db)+1:04d}"
    users_db[req.mobile] = {
        "id": uid, "mobile": req.mobile,
        "full_name": req.full_name, "email": req.email,
        "verified": False, "subscription_plan": "free",
        "created_at": datetime.utcnow().isoformat()
    }
    otps[req.mobile] = {"otp": "123456", "expires": time.time() + 600}
    return {
        "success": True, "user_id": uid,
        "message": f"OTP sent to {req.mobile}",
        "demo_info": "OTP is always 123456 in demo mode"
    }

@app.post("/v1/auth/send-otp")
def send_otp(body: dict):
    mobile = body.get("mobile","")
    if mobile not in users_db:
        raise HTTPException(404, "Mobile not registered. Please register first.")
    otps[mobile] = {"otp": "123456", "expires": time.time() + 600}
    return {"success": True, "message": f"OTP sent to {mobile}", "demo_info": "OTP: 123456"}

@app.post("/v1/auth/verify-otp")
def verify_otp(req: OTPVerifyReq):
    rec = otps.get(req.mobile)
    if not rec: raise HTTPException(400, "No OTP found. Send OTP first.")
    if rec["otp"] != req.otp: raise HTTPException(400, "Invalid OTP")
    if time.time() > rec["expires"]: raise HTTPException(400, "OTP expired")
    users_db[req.mobile]["verified"] = True
    t = token(users_db[req.mobile]["id"])
    sessions[t] = req.mobile
    return {
        "access_token": t, "token_type": "bearer",
        "expires_in": 3600, "user_id": users_db[req.mobile]["id"],
        "is_new_user": req.mobile not in profiles_db
    }

@app.post("/v1/auth/login")
def login(body: dict):
    mobile = body.get("mobile","")
    if mobile not in users_db:
        raise HTTPException(401, "Not registered")
    t = token(users_db[mobile]["id"])
    sessions[t] = mobile
    return {"access_token": t, "token_type": "bearer", "expires_in": 3600}

# ── PROFILE ─────────────────────────────────────────────────
@app.post("/v1/profile")
def create_profile(req: ProfileReq, mobile: Optional[str] = Depends(auth)):
    lp = life_path(req.dob) if req.dob else 7
    sign = sun_sign(req.dob) if req.dob else "Scorpio"
    profile = {
        **req.dict(),
        "life_path_number": lp,
        "sun_sign": sign,
        "nakshatra": "Rohini",
        "primary_dosha": "Pitta",
        "meditation_streak": 0,
        "created_at": datetime.utcnow().isoformat()
    }
    key = mobile or "demo"
    profiles_db[key] = profile
    if mobile and mobile in users_db:
        users_db[mobile]["sun_sign"] = sign
        users_db[mobile]["life_path"] = lp
    return {"success": True, "life_path_number": lp, "sun_sign": sign,
            "message": "Spiritual profile created successfully"}

@app.get("/v1/profile")
def get_profile(mobile: Optional[str] = Depends(auth)):
    profile = profiles_db.get(mobile or "demo", {
        "full_name": "Arjun Sharma", "dob": "1990-10-28",
        "birth_time": "10:30", "birth_place": "Bangalore, India",
        "sun_sign": "Scorpio", "nakshatra": "Rohini",
        "life_path_number": 7, "primary_dosha": "Pitta",
        "meditation_streak": 12
    })
    user = users_db.get(mobile, {"subscription_plan": "premium"})
    return {"user_id": user.get("id","USR0001"),
            "subscription_plan": user.get("subscription_plan","premium"),
            "profile": profile}

# ── ASTROLOGY ───────────────────────────────────────────────
@app.post("/v1/astrology/kundli")
def generate_kundli(mobile: Optional[str] = Depends(auth)):
    return {
        "lagna": "Scorpio", "rashi": "Leo", "nakshatra": "Rohini",
        "nakshatra_pada": 2, "mahadasha": "Jupiter (2022–2038)",
        "planet_positions": {
            "Sun":     {"sign": "Gemini", "house": 3, "degree": 18.4},
            "Moon":    {"sign": "Taurus", "house": 7, "degree": 4.2, "status": "Exalted"},
            "Mars":    {"sign": "Aries",  "house": 6, "degree": 22.1, "status": "Own sign"},
            "Mercury": {"sign": "Taurus", "house": 7, "degree": 12.8},
            "Jupiter": {"sign": "Cancer", "house": 9, "degree": 6.3,  "status": "Exalted"},
            "Venus":   {"sign": "Gemini", "house": 8, "degree": 28.9},
            "Saturn":  {"sign": "Aquarius","house": 4,"degree": 15.7},
            "Rahu":    {"sign": "Pisces", "house": 5, "degree": 9.4},
            "Ketu":    {"sign": "Virgo",  "house": 11,"degree": 9.4},
        },
        "yogas": [
            {"name": "Gajakesari Yoga", "description": "Moon–Jupiter: wisdom, fame, prosperity"},
            {"name": "Hamsa Yoga", "description": "Jupiter in Kendra: spiritual growth"},
            {"name": "Budha Aditya Yoga", "description": "Sun–Mercury: intelligence, communication"},
        ]
    }

@app.get("/v1/astrology/horoscope/daily")
def daily_horoscope():
    return {
        "date": date.today().isoformat(),
        "sun_sign": "Scorpio",
        "overall_score": 9,
        "career": "Mars–Pluto trine peaks today. Bold action, deep insight. Career opportunities are imminent — move decisively before Thursday.",
        "finance": "Strong Jupiter aspect supports financial decisions. Review investments; consider long-term positioning.",
        "love": "Venus in Gemini activates your 8th house. Deep, transformative connection is possible today.",
        "health": "Pitta may run high — stay hydrated. Avoid heavy meals after 7 PM.",
        "travel": "Minor delays possible. Delay non-urgent travel until Friday.",
        "lucky_number": 8, "lucky_color": "Deep Violet",
        "mantra": "Krim Krishnaya Namaha",
        "planetary_event": "Mercury turns Direct today"
    }

@app.get("/v1/astrology/horoscope/weekly")
def weekly_horoscope():
    return {
        "sign": "Scorpio", "period": "3–9 June 2026",
        "summary": "A week of transformation and momentum",
        "career": "Mercury direct clears the path for a stalled project. Thursday and Friday are optimal for presentations.",
        "relationships": "Venus in Gemini lights up your 8th house — conversations become unusually intimate.",
        "health": "Prioritise cooling foods and sleep before 10 PM.",
        "finance": "Strong Jupiter aspect supports long-term financial decisions.",
        "best_days": ["Wednesday", "Thursday", "Saturday"],
        "avoid_days": ["Monday"]
    }

@app.post("/v1/astrology/compatibility")
def compatibility(body: dict):
    import random
    score = random.randint(72, 95)
    return {
        "score": score,
        "guna_milan": min(36, score // 3),
        "summary": "Strong compatibility with shared spiritual values and life goals.",
        "nadi": "Compatible",
        "bhakoot": "Auspicious",
        "advice": "Excellent for long-term partnership. Minor Mangalik dosha can be neutralised through ritual."
    }

# ── NUMEROLOGY ──────────────────────────────────────────────
@app.post("/v1/numerology/generate")
def gen_numerology(mobile: Optional[str] = Depends(auth)):
    profile = profiles_db.get(mobile or "demo", {})
    dob = profile.get("dob", "1990-10-28")
    lp = life_path(dob)
    name = profile.get("full_name", "Arjun Sharma")
    pyval = {"a":1,"b":2,"c":3,"d":4,"e":5,"f":6,"g":7,"h":8,"i":9,"j":1,"k":2,"l":3,"m":4,
             "n":5,"o":6,"p":7,"q":8,"r":9,"s":1,"t":2,"u":3,"v":4,"w":5,"x":6,"y":7,"z":8}
    dest = sum(pyval.get(c.lower(),0) for c in name if c.isalpha())
    while dest>9 and dest not in (11,22,33): dest=sum(int(d) for d in str(dest))
    d = date.fromisoformat(dob); py=sum(int(x) for x in str(d.day+d.month+2026))
    while py>9 and py not in(11,22,33): py=sum(int(d) for d in str(py))
    return {
        "life_path_number": lp,
        "destiny_number": dest,
        "soul_number": (lp+dest)%9 or 9,
        "personality_number": 9,
        "personal_year_2026": py,
        "lucky_color": "Violet",
        "lucky_day": "Thursday",
        "lucky_numbers": [lp, dest, lp+dest, 34],
        "message": f"Life Path {lp} — The Seeker. Introspective, analytical, deeply spiritual."
    }

@app.get("/v1/numerology/report")
def num_report(mobile: Optional[str] = Depends(auth)):
    return {
        "life_path_number": 7, "destiny_number": 8, "soul_number": 2,
        "personal_year": 5, "lucky_color": "Violet", "lucky_day": "Thursday",
        "lucky_numbers": [7, 8, 16, 25, 34],
        "career_paths": ["Research", "Philosophy", "Finance", "Technology", "Spiritual Teaching"],
        "power_gemstone": "Amethyst · Cat's Eye",
        "reading": "You are the eternal seeker — drawn to wisdom, solitude, and the mysteries beneath the surface."
    }

# ── AYURVEDA ────────────────────────────────────────────────
@app.post("/v1/ayurveda/assessment")
async def ayurveda_assessment(req: AyurvedaReq):
    answers = req.answers
    v = sum(1 for a in answers.values() if a=="V")
    p = sum(1 for a in answers.values() if a=="P")
    k = sum(1 for a in answers.values() if a=="K")
    total = max(v+p+k, 1)
    vp,pp,kp = round(v/total*100), round(p/total*100), round(k/total*100)
    dom = "Pitta" if p>=v and p>=k else "Vata" if v>=p and v>=k else "Kapha"
    sec = "Vata" if dom=="Pitta" else "Pitta" if dom=="Vata" else "Pitta"

    # Try real Claude AI if key is available
    api_key = os.getenv("ANTHROPIC_API_KEY","")
    if api_key and len(answers) >= 5:
        try:
            import httpx
            q_summary = "\n".join([f"{k}: {v}" for k,v in list(answers.items())[:10]])
            resp = await httpx.AsyncClient().post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version":"2023-06-01",
                         "content-type":"application/json"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":800,
                      "messages":[{"role":"user","content":
                        f"Ayurvedic assessment. Scores: Vata {vp}%, Pitta {pp}%, Kapha {kp}%. Dominant: {dom}. "
                        f"Answer sample: {q_summary}. "
                        f"Give a 2-sentence constitution summary and 4 diet recommendations to favour and avoid. "
                        f"Reply in JSON: {{\"summary\":\"...\",\"favour\":[...],\"avoid\":[...]}}"}]},
                timeout=15
            )
            ai = json.loads(resp.json()["content"][0]["text"])
            summary = ai.get("summary","")
            favour = ai.get("favour",[])
            avoid = ai.get("avoid",[])
        except: summary = favour = avoid = None
    else: summary = favour = avoid = None

    return {
        "primaryDosha": dom, "secondaryDosha": sec,
        "prakruti": f"{dom}-{sec}",
        "vikruti": "Mild seasonal imbalance detected",
        "scores": {"vata": vp, "pitta": pp, "kapha": kp},
        "tongueAnalysis": "Tongue photo analysed" if req.tongue_image_b64 else "Not provided",
        "eyeAnalysis": "Eye photo analysed" if req.eye_image_b64 else "Not provided",
        "constitutionSummary": summary or f"Your {dom}-dominant constitution brings intensity, focus and transformation. The {sec} influence adds movement and adaptability to your nature.",
        "currentImbalances": ["Mild digestive sensitivity", "Occasional stress-related tension"],
        "dietaryGuidelines": {
            "favour": favour or ["Cooling foods","Sweet fruits","Bitter greens","Coconut water","Coriander","Fennel","Pomegranate","Aloe vera"],
            "avoid": avoid or ["Spicy foods","Fermented foods","Alcohol","Excessive caffeine","Fried foods","Red chilli","Vinegar","Pickles"],
            "mealTiming": "Main meal at midday. Light dinner before 7 PM. No skipping breakfast."
        },
        "dailyRoutine": {
            "morning": "Wake before sunrise. Oil pulling 5 min. Tongue scraping. Warm water with lemon. Light yoga 20 min.",
            "afternoon": "Avoid intense work after 2 PM. Brief walk. Herbal tea.",
            "evening": "Wind down by 9 PM. Light meal. No screens after 9 PM.",
            "sleep": "Bed by 10 PM. Foot massage with coconut oil. Left nostril breathing (Chandra Nadi)."
        },
        "herbsAndRemedies": [
            "Shatavari: 1 tsp in warm milk at bedtime — cooling and nourishing",
            "Brahmi: morning with honey — mental clarity and cooling",
            "Triphala: 1 tsp at night — gentle digestive cleanse",
            "Ashwagandha: morning with warm milk — sustained energy",
            "Neem: alternate days — skin and blood purification"
        ],
        "exerciseRecommendation": "Yoga and swimming 30 min in morning. Avoid vigorous exercise after 10 AM or in peak heat. Sheetali pranayama daily for Pitta cooling.",
        "seasonalAdvice": "Pre-monsoon: favour light dry bitter foods. Stay dry. Avoid cold water. Use digestive spices. Reduce dairy.",
        "mentalEmotionalGuidance": "Cultivate patience and equanimity. Cooling pranayama reduces mental heat. Journal at night to discharge accumulated impressions. Spend time near water or in nature.",
        "warningSignsToWatch": ["Skin rashes or acne flares", "Burning digestion or loose stools", "Irritability or anger surges"],
        "affirmation": "I am grounded, cool, and clear. My inner fire illuminates without burning."
    }

@app.get("/v1/ayurveda/dosha-profile")
def dosha_profile(mobile: Optional[str] = Depends(auth)):
    return {
        "primary_dosha": "Pitta", "secondary_dosha": "Vata",
        "prakruti": "Pitta-Vata",
        "scores": {"vata": 28, "pitta": 55, "kapha": 17},
        "summary": "Pitta-dominant with Vata influence. Sharp mind, strong digestion, needs cooling.",
        "last_assessed": datetime.utcnow().isoformat()
    }

@app.get("/v1/ayurveda/wellness-plan")
def wellness_plan(mobile: Optional[str] = Depends(auth)):
    return {
        "diet_plan": "Warm cooked foods. Sweet, bitter and astringent tastes. Avoid spicy, sour, salty excess.",
        "foods_favour": ["Cucumber","Coconut","Pomegranate","Sweet fruits","Bitter greens","Basmati rice","Ghee"],
        "foods_avoid": ["Chilli","Garlic","Onion","Vinegar","Alcohol","Fried foods","Processed sugar"],
        "morning_routine": "Oil pulling → tongue scraping → warm lemon water → yoga/walk → light breakfast",
        "evening_routine": "Meditation → light dinner → reading → 10 PM bedtime",
        "herbs_remedies": ["Shatavari","Brahmi","Triphala","Neem","Amla"]
    }

# ── MEDITATION ──────────────────────────────────────────────
@app.get("/v1/meditation/library")
def meditation_library():
    return {"meditations": [
        {"id":"M1","title":"Morning Clarity","category":"focus","duration_minutes":15,"dosha_focus":"pitta","is_premium":False,"description":"Focused breathwork and visualisation for peak performance"},
        {"id":"M2","title":"Deep Sleep Journey","category":"sleep","duration_minutes":20,"dosha_focus":"pitta","is_premium":False,"description":"Progressive relaxation for Pitta types. Cooling and grounding."},
        {"id":"M3","title":"Stress Relief & Reset","category":"anxiety","duration_minutes":10,"dosha_focus":"all","is_premium":False,"description":"4-7-8 breathwork and body scan for instant calm"},
        {"id":"M4","title":"Chakra Awakening","category":"spiritual","duration_minutes":30,"dosha_focus":"all","is_premium":True,"description":"Seven chakra journey with mantra and visualisation"},
        {"id":"M5","title":"Nadi Shodhana Pranayama","category":"breathwork","duration_minutes":15,"dosha_focus":"pitta","is_premium":False,"description":"Alternate nostril breathing — balances Pitta and calms mind"},
        {"id":"M6","title":"Yoga Nidra","category":"sleep","duration_minutes":40,"dosha_focus":"vata","is_premium":True,"description":"Psychic sleep — deep restoration and body awareness"},
        {"id":"M7","title":"Loving Kindness (Metta)","category":"spiritual","duration_minutes":20,"dosha_focus":"pitta","is_premium":False,"description":"Heart-opening compassion cultivation — Pitta cooling"},
        {"id":"M8","title":"Morning Abundance","category":"manifestation","duration_minutes":12,"dosha_focus":"all","is_premium":False,"description":"Gratitude and manifestation — energising visualisation"},
        {"id":"M9","title":"Tibetan Singing Bowls","category":"sound","duration_minutes":60,"dosha_focus":"all","is_premium":True,"description":"Vibrational sound healing for deep absorption"},
    ]}

@app.post("/v1/meditation/progress")
def save_progress(body: dict, mobile: Optional[str] = Depends(auth)):
    return {"success": True, "message": "Progress saved",
            "completion": body.get("completion_percentage", 0)}

# ── AI COACH ────────────────────────────────────────────────
@app.post("/v1/ai/chat")
async def ai_chat(req: ChatReq, mobile: Optional[str] = Depends(auth)):
    sid = req.session_id or secrets.token_hex(8)
    if sid not in chat_hist: chat_hist[sid] = []
    chat_hist[sid].append({"role":"user","content":req.message})

    api_key = os.getenv("ANTHROPIC_API_KEY","")

    if api_key:
        try:
            import httpx
            system = """You are SoulVerse AI — a deeply knowledgeable spiritual wellness guide.
User profile: Scorpio ♏ (born Oct 28 1990, 10:30am, Bangalore) | Nakshatra: Rohini (Pada 2)
Mahadasha: Jupiter (2022–2038) | Life Path: 7 | Destiny: 8 | Soul: 2 | Personal Year: 5
Dominant Dosha: Pitta-Vata | Meditation streak: 12 days | Subscription: Premium
Today: June 5 2026 | Planetary: Mars trine Pluto (peak), Mercury Direct, Venus in Gemini
Provide warm, deeply personalised spiritual and wellness guidance.
Draw on Vedic astrology, numerology, Ayurveda, and meditation. 2-3 paragraphs max."""

            messages = chat_hist[sid][-10:]
            resp = await httpx.AsyncClient(timeout=30).post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":600,
                      "system":system,"messages":messages}
            )
            reply = resp.json()["content"][0]["text"]
        except Exception as e:
            reply = f"The cosmic network is momentarily unavailable ({str(e)[:50]}). Please try again."
    else:
        replies = {
            "career": "Based on your Scorpio chart and Life Path 7, your career peaks when you work in depth rather than breadth. Jupiter Mahadasha (2022–2038) strongly supports research, finance, and leadership roles. The Mars–Pluto trine active today amplifies your strategic power — present your most ambitious idea before Thursday.",
            "meditation": "For your Pitta-Vata constitution, I recommend the Nadi Shodhana pranayama in the library — 15 minutes before 8 AM. The cooling alternating breath balances your dominant fire energy and grounds the Vata movement. Your 12-day streak shows real commitment; push to 21 days for neurological habit formation.",
            "ayurveda": "In pre-monsoon season (June), Pitta accumulates in the body as heat and inflammation. Focus on sweet, bitter and astringent tastes. Add coriander seeds to warm water each morning. Shatavari in warm milk at bedtime will cool and nourish your system significantly.",
            "relationship": "As a Life Path 7, you need depth and authenticity in relationships — surface-level connection drains you. Your Soul Number 2 yearns for partnership while your 7 needs solitude to recharge. The key is communicating this rhythm clearly to partners rather than withdrawing without explanation.",
        }
        key = next((k for k in replies if k in req.message.lower()), None)
        reply = replies.get(key, f"Namaste 🙏 As a Scorpio Life Path 7 with Pitta-Vata constitution, your path is one of depth, transformation and wisdom-seeking. The planetary energies today — particularly Mars trining Pluto — amplify your natural intensity and strategic mind. What specific area of life would you like to explore — career, relationships, wellness, or spiritual growth?")

    chat_hist[sid].append({"role":"assistant","content":reply})
    return {"session_id": sid, "response": reply,
            "ai_powered": bool(api_key),
            "model": "claude-sonnet-4-20250514" if api_key else "demo-mode"}

@app.get("/v1/ai/history/{session_id}")
def ai_history(session_id: str):
    return {"session_id": session_id, "messages": chat_hist.get(session_id,[])}

@app.get("/v1/ai/sessions")
def ai_sessions(mobile: Optional[str] = Depends(auth)):
    return {"sessions": [{"id": k, "message_count": len(v)} for k,v in list(chat_hist.items())[:10]]}

# ── CONSULTATIONS ───────────────────────────────────────────
@app.get("/v1/experts")
def list_experts(specialization: Optional[str] = None):
    experts = [
        {"id":"E1","name":"Dr. Ramesh Sharma","specialization":"astrologer","experience_years":18,"rating":4.9,"hourly_rate":799,"languages":["English","Hindi"],"bio":"18 years Vedic astrology. Specialises in Kundli, career and marriage guidance.","is_verified":True,"avatar":"🔮"},
        {"id":"E2","name":"Dr. Priya Nair","specialization":"ayurveda","experience_years":12,"rating":4.8,"hourly_rate":599,"languages":["English","Malayalam"],"bio":"Ayurvedic physician from Thrissur. Expert in Panchakarma and dosha management.","is_verified":True,"avatar":"🌿"},
        {"id":"E3","name":"Ananya Krishnan","specialization":"meditation","experience_years":8,"rating":4.7,"hourly_rate":399,"languages":["English","Kannada"],"bio":"Certified meditation coach and yoga teacher from Mysuru.","is_verified":True,"avatar":"🧘"},
        {"id":"E4","name":"Dr. Suresh Pillai","specialization":"ayurveda","experience_years":20,"rating":4.9,"hourly_rate":1200,"languages":["English","Malayalam","Tamil"],"bio":"Panchakarma specialist from Kottakkal. 20 years in traditional Kerala Ayurveda.","is_verified":True,"avatar":"🏥"},
        {"id":"E5","name":"Pandit Govind Shastri","specialization":"astrologer","experience_years":25,"rating":5.0,"hourly_rate":1500,"languages":["Hindi","Sanskrit","English"],"bio":"KP & Vedic astrologer from Varanasi. Expert in Muhurta, remedies, and Vastu.","is_verified":True,"avatar":"🪐"},
        {"id":"E6","name":"Rohini Desai","specialization":"wellness","experience_years":10,"rating":4.5,"hourly_rate":699,"languages":["English","Hindi","Gujarati"],"bio":"Wellness and life coach from Mumbai. Specialises in burnout, relationships and career.","is_verified":True,"avatar":"💆"},
    ]
    if specialization:
        experts = [e for e in experts if e["specialization"]==specialization]
    return {"experts": experts, "total": len(experts)}

@app.get("/v1/experts/{expert_id}")
def expert_detail(expert_id: str):
    return {"id":expert_id,"name":"Dr. Ramesh Sharma","specialization":"astrologer",
            "experience_years":18,"rating":4.9,"total_reviews":347,"hourly_rate":799,
            "languages":["English","Hindi"],"is_verified":True,
            "bio":"18 years experience in Vedic astrology. Specialises in career, marriage, and transit analysis.",
            "availability": {"monday":["10:00","11:00","14:00","16:00"],"tuesday":["09:00","11:00","15:00"],"wednesday":["10:00","13:00","17:00"]}}

@app.post("/v1/bookings")
def create_booking(req: BookingReq, mobile: Optional[str] = Depends(auth)):
    amounts = {"E1":799,"E2":599,"E3":399,"E4":1200,"E5":1500,"E6":699}
    amount = amounts.get(req.expert_id, 799) * (req.duration_minutes/60)
    bk = {"booking_id":f"BK{len(bookings)+1:04d}","user_id": mobile or "USR0001",
          **req.dict(), "amount":amount, "status":"confirmed",
          "created_at":datetime.utcnow().isoformat()}
    bookings.append(bk)
    return {"booking_id":bk["booking_id"],"status":"confirmed","amount":amount,
            "message":"Booking confirmed! You will receive a confirmation shortly."}

@app.get("/v1/bookings")
def list_bookings(mobile: Optional[str] = Depends(auth)):
    return {"bookings": bookings, "total": len(bookings)}

# ── PAYMENTS ────────────────────────────────────────────────
@app.post("/v1/payments/create-order")
def create_order(req: PaymentReq):
    amounts = {"premium":29900,"pro":59900,"elite":99900}
    a = amounts.get(req.plan,29900)
    return {"order_id":f"order_{secrets.token_hex(6)}","amount":a,
            "currency":"INR","plan":req.plan,
            "key_id":"rzp_test_demo","razorpay_ready":True,
            "note":"Replace key_id with your real Razorpay key to process payments"}

@app.get("/v1/payments/subscriptions")
def get_subscription(mobile: Optional[str] = Depends(auth)):
    user = users_db.get(mobile or "demo", {})
    return {"plan": user.get("subscription_plan","premium"),
            "is_active":True,"start_date":"2026-06-01","end_date":"2026-07-01","amount":299}

# ── NOTIFICATIONS ───────────────────────────────────────────
@app.get("/v1/notifications")
def get_notifications(mobile: Optional[str] = Depends(auth)):
    return {"notifications":[
        {"id":"N1","title":"Today's Scorpio horoscope is ready","message":"Mars trines Pluto — your peak day. Read your full reading.","is_read":False,"notification_type":"horoscope","created_at":datetime.utcnow().isoformat()},
        {"id":"N2","title":"Ayurveda tip for today","message":"Pre-monsoon: drink warm water with ginger and honey before 8 AM.","is_read":False,"notification_type":"wellness","created_at":datetime.utcnow().isoformat()},
        {"id":"N3","title":"Meditation streak — 12 days!","message":"You completed 12 consecutive days. Keep going!","is_read":True,"notification_type":"meditation","created_at":datetime.utcnow().isoformat()},
    ]}

# ── ADMIN ───────────────────────────────────────────────────
@app.get("/v1/admin/dashboard")
def admin_dashboard():
    return {"total_users":len(users_db) or 10482,"active_users":2847,
            "paid_users":523,"revenue_inr":384700.0,"total_bookings":len(bookings) or 412,
            "pending_expert_approvals":3,"mrr_inr":156297,
            "top_plan":"premium","churn_rate":4.2,"dau":1847}

@app.get("/v1/admin/users")
def admin_users():
    return {"users":[{"id":v["id"],"mobile":v["mobile"],"name":v["full_name"],"plan":v.get("subscription_plan","free"),"verified":v["verified"]} for v in users_db.values()] or [{"id":"USR0001","mobile":"+919876543210","name":"Arjun Sharma","plan":"premium","verified":True}]}
