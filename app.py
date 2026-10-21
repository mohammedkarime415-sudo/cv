import hashlib
import hmac
import html
import os
import time
 
import requests
import streamlit as st
 
from io import BytesIO
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
 
 
# ---------------------------------------------------
# Configuration
# ---------------------------------------------------
 
N8N_WEBHOOK_URL = "http://n8n:5678/webhook/cv-personalizer"
 
st.set_page_config(
    page_title="CV Personalizer",
    page_icon="📄",
    layout="wide",
)
 
 
# ---------------------------------------------------
# Design : palette inspirée du visuel
# bleu nuit + néon cyan + titre orange + pixel art
# ---------------------------------------------------
 
NAVY = "#050B2E"
NAVY_2 = "#0A1450"
ORANGE = "#FF6B1A"
CYAN = "#19D3FF"
PINK = "#FF3D7F"
MUTED = "#A9B4E0"
 
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
 
:root {
    --navy: #050B2E;
    --navy-2: #0A1450;
    --panel: rgba(12, 22, 84, 0.62);
    --orange: #FF6B1A;
    --cyan: #19D3FF;
    --pink: #FF3D7F;
    --muted: #A9B4E0;
}
 
html, body, [class*="css"], .stApp {
    font-family: 'Poppins', sans-serif;
}
 
/* ---------- Fond de page ---------- */
.stApp {
    color: #FFFFFF;
    background:
        radial-gradient(circle at 8% 4%, rgba(25, 211, 255, 0.22), transparent 38%),
        radial-gradient(circle at 96% 12%, rgba(255, 61, 127, 0.16), transparent 34%),
        radial-gradient(circle at 50% 100%, rgba(40, 70, 200, 0.28), transparent 50%),
        linear-gradient(180deg, #050B2E 0%, #08124A 100%);
    background-attachment: fixed;
}
 
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }
footer { visibility: hidden; }
 
.block-container {
    max-width: 1180px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}
 
/* ---------- Texte global ---------- */
.stApp p, .stApp li, .stApp label, .stApp span { color: #FFFFFF; }
[data-testid="stWidgetLabel"] p {
    color: #FFFFFF !important;
    font-weight: 600;
}
 
/* ---------- Hero ---------- */
.hero {
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
    padding: 2.6rem 2.8rem;
    margin-bottom: 2rem;
    border-radius: 22px;
    border: 1px solid rgba(25, 211, 255, 0.28);
    background:
        radial-gradient(circle at 12% 90%, rgba(25, 211, 255, 0.18), transparent 40%),
        linear-gradient(120deg, #060D3A 0%, #0B1760 100%);
    box-shadow: 0 0 40px rgba(25, 211, 255, 0.12), inset 0 0 60px rgba(5, 11, 46, 0.6);
}
.hero .bokeh {
    position: absolute;
    border-radius: 50%;
    filter: blur(2px);
    pointer-events: none;
}
.hero .b1 { width: 70px;  height: 70px;  left: 46%; top: 10%;   background: rgba(180, 190, 255, 0.14); }
.hero .b2 { width: 54px;  height: 54px;  left: 58%; top: 62%;   background: rgba(25, 211, 255, 0.16); }
.hero .b3 { width: 110px; height: 110px; right: -30px; bottom: -40px; background: rgba(255, 61, 127, 0.22); }
.hero-text { position: relative; z-index: 2; flex: 1 1 52%; }
.hero h1 {
    margin: 0;
    padding: 0;
    font-weight: 800;
    font-size: clamp(2rem, 4.4vw, 3.4rem);
    line-height: 1.05;
    letter-spacing: 0.01em;
    text-transform: uppercase;
    color: var(--orange);
}
.hero .sub {
    margin: 0.7rem 0 0 0;
    font-weight: 700;
    font-size: clamp(1.05rem, 2vw, 1.5rem);
    text-transform: uppercase;
    color: #FFFFFF;
}
.hero .lead {
    margin: 1.1rem 0 0 0;
    max-width: 52ch;
    font-size: 0.98rem;
    line-height: 1.6;
    color: var(--muted);
}
.hero-art { position: relative; z-index: 2; flex: 1 1 44%; max-width: 460px; }
.hero-art svg { width: 100%; height: auto; display: block; }
 
@media (max-width: 820px) {
    .hero { flex-direction: column; align-items: flex-start; padding: 1.8rem 1.4rem; }
    .hero-art { max-width: 100%; width: 100%; }
}
 
/* ---------- En-têtes d'étape ---------- */
.step {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    margin: 0.2rem 0 0.9rem 0;
}
.step .badge {
    flex: 0 0 auto;
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    color: var(--cyan);
    border: 2px solid var(--cyan);
    box-shadow: 0 0 14px rgba(25, 211, 255, 0.55), inset 0 0 10px rgba(25, 211, 255, 0.25);
}
.step .t { font-weight: 700; font-size: 1.2rem; color: #FFFFFF; line-height: 1.2; }
.step .d { font-size: 0.88rem; color: var(--muted); margin-top: 2px; }
 
/* ---------- Cartes (st.container(border=True)) ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--panel);
    border: 1px solid rgba(25, 211, 255, 0.30) !important;
    border-radius: 18px !important;
    padding: 0.6rem 0.8rem;
    box-shadow: 0 0 24px rgba(25, 211, 255, 0.07);
}
 
/* ---------- Champs ---------- */
.stTextArea textarea {
    background: #08114A !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(25, 211, 255, 0.40) !important;
    border-radius: 12px !important;
}
.stTextArea textarea::placeholder { color: #7683BD !important; }
.stTextArea textarea:focus {
    border-color: var(--cyan) !important;
    box-shadow: 0 0 0 1px var(--cyan), 0 0 16px rgba(25, 211, 255, 0.35) !important;
}
 
[data-testid="stFileUploaderDropzone"] {
    background: #08114A;
    border: 2px dashed rgba(25, 211, 255, 0.55);
    border-radius: 14px;
}
[data-testid="stFileUploaderDropzone"] * { color: var(--muted) !important; }
[data-testid="stFileUploaderDropzone"] button {
    background: transparent;
    border: 1px solid var(--cyan);
    color: var(--cyan) !important;
    border-radius: 10px;
}
[data-testid="stFileUploaderDropzone"] button * { color: var(--cyan) !important; }
 
/* ---------- Connexion ---------- */
[data-testid="stForm"] {
    background: var(--panel);
    border: 1px solid rgba(25, 211, 255, 0.35);
    border-radius: 20px;
    padding: 1.6rem 1.6rem 1.2rem 1.6rem;
    box-shadow: 0 0 30px rgba(25, 211, 255, 0.12);
}
[data-baseweb="input"] {
    background: #08114A !important;
    border: 1px solid rgba(25, 211, 255, 0.40) !important;
    border-radius: 12px !important;
}
[data-baseweb="input"]:focus-within {
    border-color: var(--cyan) !important;
    box-shadow: 0 0 0 1px var(--cyan), 0 0 16px rgba(25, 211, 255, 0.35) !important;
}
[data-baseweb="input"] input {
    background: transparent !important;
    color: #FFFFFF !important;
}
[data-baseweb="input"] input::placeholder { color: #7683BD !important; }
[data-baseweb="input"] button, [data-baseweb="input"] svg { color: var(--cyan) !important; fill: var(--cyan) !important; }
.stFormSubmitButton > button {
    width: 100%;
    border: none;
    border-radius: 12px;
    padding: 0.7rem 1.6rem;
    font-weight: 700;
    font-family: 'Poppins', sans-serif;
    color: #FFFFFF;
    background: linear-gradient(90deg, #FF6B1A, #FF8F3A);
    box-shadow: 0 0 22px rgba(255, 107, 26, 0.45);
}
.stFormSubmitButton > button * { color: #FFFFFF !important; }
.stFormSubmitButton > button:hover { box-shadow: 0 0 30px rgba(255, 107, 26, 0.70); }
.login-title { font-weight: 800; font-size: 1.5rem; color: #FFFFFF; margin: 0 0 0.2rem 0; }
.login-sub { font-size: 0.9rem; color: var(--muted); margin: 0 0 1rem 0; }
.userbar { color: var(--muted); font-size: 0.9rem; padding-top: 0.55rem; }
.userbar b { color: var(--cyan); }
 
/* ---------- Boutons ---------- */
.stButton > button, .stDownloadButton > button {
    border-radius: 12px;
    font-weight: 700;
    padding: 0.7rem 1.6rem;
    font-family: 'Poppins', sans-serif;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #FF6B1A, #FF8F3A);
    color: #FFFFFF;
    border: none;
    box-shadow: 0 0 22px rgba(255, 107, 26, 0.45);
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 0 30px rgba(255, 107, 26, 0.70);
    color: #FFFFFF;
}
.stButton > button[kind="secondary"],
.stDownloadButton > button {
    background: transparent;
    color: var(--cyan);
    border: 2px solid var(--cyan);
    box-shadow: 0 0 16px rgba(25, 211, 255, 0.35);
}
.stButton > button[kind="secondary"] *,
.stDownloadButton > button * { color: var(--cyan) !important; }
.stButton > button[kind="secondary"]:hover,
.stDownloadButton > button:hover {
    background: rgba(25, 211, 255, 0.12);
    box-shadow: 0 0 26px rgba(25, 211, 255, 0.6);
}
.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible {
    outline: 3px solid #FFFFFF;
    outline-offset: 2px;
}
 
/* ---------- Cases à cocher ---------- */
[data-testid="stCheckbox"] label p { color: #FFFFFF !important; }
[data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child {
    border-color: var(--cyan) !important;
}
 
/* ---------- Expander ---------- */
[data-testid="stExpander"] {
    background: rgba(8, 17, 74, 0.7);
    border: 1px solid rgba(25, 211, 255, 0.28);
    border-radius: 12px;
}
[data-testid="stExpander"] summary p { color: var(--cyan) !important; font-weight: 600; }
 
/* ---------- Alertes natives ---------- */
[data-testid="stAlert"] {
    border-radius: 12px;
    background: rgba(8, 17, 74, 0.85);
    border: 1px solid rgba(25, 211, 255, 0.35);
}
 
/* ---------- Mots-clés ---------- */
.group-title { font-weight: 700; font-size: 1.02rem; margin: 0.2rem 0 0.7rem 0; color: #FFFFFF; }
.chips { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.4rem; }
.chip {
    display: inline-block;
    padding: 0.38rem 0.85rem;
    border-radius: 999px;
    font-size: 0.88rem;
    font-weight: 600;
}
.chip.ok {
    color: var(--cyan);
    background: rgba(25, 211, 255, 0.10);
    border: 1px solid rgba(25, 211, 255, 0.65);
    box-shadow: 0 0 10px rgba(25, 211, 255, 0.25);
}
.chip.ko {
    color: #FF86AB;
    background: rgba(255, 61, 127, 0.10);
    border: 1px solid rgba(255, 61, 127, 0.70);
    box-shadow: 0 0 10px rgba(255, 61, 127, 0.25);
}
.empty { color: var(--muted); font-size: 0.92rem; }
 
/* ---------- Score ---------- */
.score { margin: 0.2rem 0 1.1rem 0; }
.score .row { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.4rem; }
.score .label { font-weight: 600; color: #FFFFFF; }
.score .value { font-weight: 800; font-size: 1.6rem; color: var(--orange); }
.score .bar { height: 10px; border-radius: 999px; background: rgba(255, 255, 255, 0.10); overflow: hidden; }
.score .fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--cyan), var(--orange));
    box-shadow: 0 0 12px rgba(25, 211, 255, 0.6);
}
 
.foot { text-align: center; color: #7683BD; font-size: 0.8rem; margin-top: 2.5rem; }
 
@media (prefers-reduced-motion: reduce) {
    .stButton > button, .stDownloadButton > button { transition: none; }
}
</style>
"""
 
 
# ---------------------------------------------------
# Illustration du hero (SVG pixel art + néon)
# ---------------------------------------------------
 
def pixel_block(pattern, x0, y0, size, color):
    rects = []
    for r, row in enumerate(pattern):
        for c, ch in enumerate(row):
            if ch == "X":
                rects.append(
                    f'<rect x="{x0 + c * size}" y="{y0 + r * size}" '
                    f'width="{size - 1}" height="{size - 1}" fill="{color}"/>'
                )
    return "".join(rects)
 
 
def hero_art():
    star = [
        "..X..",
        "..X..",
        "XXXXX",
        ".XXX.",
        "XX.XX",
    ]
 
    # --- CV (à gauche) ---
    cv_bars = [
        (60, 128, 56, PINK), (60, 142, 110, "#FFFFFF"), (60, 155, 92, CYAN), (60, 168, 100, "#FFFFFF"),
        (60, 188, 48, PINK), (60, 202, 105, CYAN), (60, 215, 80, "#FFFFFF"),
    ]
    cv = "".join(
        f'<rect x="{x}" y="{y}" width="{w}" height="5" rx="2.5" fill="{c}" opacity="0.9"/>'
        for x, y, w, c in cv_bars
    )
    pills = "".join(
        f'<rect x="{x}" y="232" width="{w}" height="10" rx="5" fill="none" stroke="{CYAN}" stroke-width="1.5"/>'
        for x, w in [(60, 34), (100, 44), (150, 30)]
    )
 
    # --- Offre d'emploi (à droite) : critères trouvés / manquants ---
    rows = ""
    for y, ok, w in [(124, True, 100), (154, True, 78), (184, False, 108), (214, True, 88)]:
        if ok:
            box = (
                f'<rect x="330" y="{y}" width="16" height="16" rx="4" fill="none" stroke="{CYAN}" stroke-width="2"/>'
                f'<polyline points="334,{y + 8} 338,{y + 12} 343,{y + 4}" fill="none" stroke="{CYAN}" stroke-width="2.2"/>'
            )
            color = "#FFFFFF"
        else:
            box = (
                f'<rect x="330" y="{y}" width="16" height="16" rx="4" fill="none" stroke="{PINK}" stroke-width="2"/>'
                f'<path d="M334 {y + 4} L342 {y + 12} M342 {y + 4} L334 {y + 12}" stroke="{PINK}" stroke-width="2.2" fill="none"/>'
            )
            color = PINK
        rows += box + f'<rect x="356" y="{y + 5}" width="{w}" height="5" rx="2.5" fill="{color}" opacity="0.9"/>'
 
    svg = (
        '<svg viewBox="0 0 520 290" xmlns="http://www.w3.org/2000/svg" role="img" '
        'aria-label="Illustration : un CV comparé à une offre d\'emploi">'
        '<defs><filter id="glow" x="-30%" y="-30%" width="160%" height="160%">'
        '<feGaussianBlur stdDeviation="3.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter></defs>'
        # circuits pointillés
        f'<path d="M232 50 H210 M288 50 H395 V60 M210 95 H310" '
        f'stroke="{CYAN}" stroke-opacity="0.55" stroke-width="2" stroke-dasharray="2 7" '
        'stroke-linecap="round" fill="none"/>'
        # badge MATCH
        f'<g filter="url(#glow)"><circle cx="260" cy="50" r="28" fill="none" stroke="{CYAN}" stroke-width="2.5"/>'
        f'<text x="260" y="55" text-anchor="middle" font-family="Poppins, sans-serif" '
        f'font-weight="700" font-size="12" fill="{CYAN}">MATCH</text></g>'
        # feuille CV
        f'<g filter="url(#glow)"><rect x="40" y="40" width="170" height="215" rx="14" fill="rgba(25,211,255,0.05)" '
        f'stroke="{CYAN}" stroke-width="2.5"/>'
        f'<circle cx="76" cy="82" r="20" fill="none" stroke="{CYAN}" stroke-width="2.5"/>'
        f'<circle cx="76" cy="77" r="6" fill="none" stroke="{CYAN}" stroke-width="2"/>'
        f'<path d="M64 95 Q76 83 88 95" fill="none" stroke="{CYAN}" stroke-width="2"/>'
        '<rect x="108" y="70" width="80" height="6" rx="3" fill="#FFFFFF"/>'
        f'<rect x="108" y="84" width="54" height="5" rx="2.5" fill="{CYAN}"/>'
        f'{cv}{pills}</g>'
        # feuille offre d'emploi
        f'<g filter="url(#glow)"><rect x="310" y="60" width="170" height="195" rx="14" fill="rgba(255,107,26,0.05)" '
        f'stroke="{CYAN}" stroke-width="2.5"/>'
        f'<rect x="330" y="82" width="72" height="8" rx="4" fill="{ORANGE}"/>'
        f'<rect x="330" y="98" width="110" height="5" rx="2.5" fill="{CYAN}" opacity="0.8"/>'
        f'{rows}</g>'
        # chevrons orange : du CV vers l'offre
        f'<g filter="url(#glow)" fill="none" stroke="{ORANGE}" stroke-width="10" stroke-linejoin="miter">'
        '<polyline points="228,122 250,144 228,166"/>'
        '<polyline points="250,122 272,144 250,166" stroke-opacity="0.55"/></g>'
        # loupe
        f'<g filter="url(#glow)" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round">'
        '<circle cx="250" cy="222" r="18"/><path d="M263 235 L280 252"/></g>'
        # étoile pixel
        f'<g filter="url(#glow)">{pixel_block(star, 488, 18, 6, PINK)}</g>'
        '</svg>'
    )
    return svg
 
 
def render_hero():
    st.markdown(
        '<div class="hero">'
        '<span class="bokeh b1"></span><span class="bokeh b2"></span><span class="bokeh b3"></span>'
        '<div class="hero-text">'
        '<h1>CV Personalizer</h1>'
        '<p class="sub">Votre CV est-il prêt pour cette offre ?</p>'
        '<p class="lead">Importez votre CV, collez une offre d’emploi, repérez les compétences '
        'manquantes, puis générez une version adaptée en PDF.</p>'
        '</div>'
        f'<div class="hero-art">{hero_art()}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
 
 
def step_header(number, title, description):
    st.markdown(
        f'<div class="step"><div class="badge">{number}</div>'
        f'<div><div class="t">{html.escape(title)}</div>'
        f'<div class="d">{html.escape(description)}</div></div></div>',
        unsafe_allow_html=True,
    )
 
 
def render_chips(items, kind, symbol):
    chips = "".join(
        f'<span class="chip {kind}">{symbol} {html.escape(str(item))}</span>'
        for item in items
    )
    st.markdown(f'<div class="chips">{chips}</div>', unsafe_allow_html=True)
 
 
# ---------------------------------------------------
# Authentification
# ---------------------------------------------------
# Les mots de passe ne sont jamais stockés en clair : on garde
# un hash PBKDF2 au format  "pbkdf2$<sel_hex>$<hash_hex>".
#
# Définir les utilisateurs dans .streamlit/secrets.toml :
#
#   [users]
#   alice = "pbkdf2$...$..."
#   bob   = "pbkdf2$...$..."
#
# Générer un hash (à lancer dans un terminal) :
#   python -c "import hashlib,os;s=os.urandom(16);print('pbkdf2$'+s.hex()+'$'+hashlib.pbkdf2_hmac('sha256',b'MonMotDePasse',s,200000).hex())"
 
PBKDF2_ROUNDS = 200_000
MAX_ATTEMPTS = 5
LOCK_SECONDS = 60
 
 
def hash_password(password, salt_hex=None):
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2${salt.hex()}${digest.hex()}"
 
 
def verify_password(password, stored):
    try:
        _, salt_hex, _ = stored.split("$")
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt_hex), stored)
 
 
def load_users():
    try:
        users = {str(k): str(v) for k, v in dict(st.secrets["users"]).items()}
    except Exception:
        users = {}
 
    if users:
        return users, False
 
    # Mode démo (aucun secret configuré)
    return {"admin": hash_password("admin123", "00" * 16)}, True
 
 
def render_login():
    users, _ = load_users()
 
    st.session_state.setdefault("login_attempts", 0)
    st.session_state.setdefault("locked_until", 0.0)
 
    render_hero()
 
    _, center, _ = st.columns([1, 1.4, 1])
 
    with center:
        with st.form("login_form"):
            st.markdown(
                '<div class="login-title">Connexion</div>'
                '<div class="login-sub">Connectez-vous pour personnaliser votre CV.</div>',
                unsafe_allow_html=True,
            )
 
            username = st.text_input("Identifiant", placeholder="Votre identifiant")
            password = st.text_input("Mot de passe", type="password", placeholder="Votre mot de passe")
            submitted = st.form_submit_button("Se connecter")
 
        if submitted:
            remaining = st.session_state.locked_until - time.time()
 
            if remaining > 0:
                st.error(f"Trop de tentatives. Réessayez dans {int(remaining) + 1} s.")
            else:
                stored = users.get(username.strip())
 
                # Vérification faite même si l'utilisateur n'existe pas
                # (temps de réponse constant)
                ok = verify_password(
                    password,
                    stored or hash_password("x", "00" * 16),
                ) and stored is not None
 
                if ok:
                    st.session_state.authenticated = True
                    st.session_state.user = username.strip()
                    st.session_state.login_attempts = 0
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    if st.session_state.login_attempts >= MAX_ATTEMPTS:
                        st.session_state.locked_until = time.time() + LOCK_SECONDS
                        st.session_state.login_attempts = 0
                        st.error(f"Trop de tentatives. Réessayez dans {LOCK_SECONDS} s.")
                    else:
                        st.error("Identifiant ou mot de passe incorrect.")
 
 
st.markdown(CSS, unsafe_allow_html=True)
 
if not st.session_state.get("authenticated"):
    render_login()
    st.stop()
 
# Barre utilisateur + déconnexion
bar_left, bar_right = st.columns([5, 1])
with bar_left:
    st.markdown(
        f'<div class="userbar">Connecté en tant que <b>{html.escape(st.session_state.get("user", ""))}</b></div>',
        unsafe_allow_html=True,
    )
with bar_right:
    if st.button("Se déconnecter", key="logout"):
        st.session_state.clear()
        st.rerun()
 
render_hero()
 
 
# ---------------------------------------------------
# Fonction : extraire le texte d'un PDF
# ---------------------------------------------------
 
def extract_text_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    cv_text = ""
 
    for page in reader.pages:
        text = page.extract_text()
        if text:
            cv_text += text + "\n"
 
    return cv_text.strip()
 
 
# ---------------------------------------------------
# Fonction : générer un PDF
# ---------------------------------------------------
 
def generate_pdf(cv_text):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
 
    margin = 50
    y_position = height - 60
 
    pdf.setTitle("CV personnalisé")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y_position, "CV Personnalisé")
 
    y_position -= 40
    pdf.setFont("Helvetica", 10)
 
    lines = simpleSplit(cv_text, "Helvetica", 10, width - 2 * margin)
 
    for line in lines:
        if y_position < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y_position = height - 50
 
        pdf.drawString(margin, y_position, line)
        y_position -= 15
 
    pdf.save()
    buffer.seek(0)
    return buffer
 
 
# ---------------------------------------------------
# Fonction : appel du workflow n8n
# ---------------------------------------------------
 
def call_n8n(cv_text, job_offer, confirmed_skills):
    return requests.post(
        N8N_WEBHOOK_URL,
        json={
            "cv": cv_text,
            "job_offer": job_offer,
            "confirmed_skills": confirmed_skills,
        },
        timeout=120,
    )
 
 
# ---------------------------------------------------
# Session State
# ---------------------------------------------------
 
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None
 
if "adapted_cv" not in st.session_state:
    st.session_state.adapted_cv = None
 
 
# ---------------------------------------------------
# Étapes 1 et 2 : CV + offre d'emploi
# ---------------------------------------------------
 
cv_text = ""
col_cv, col_offer = st.columns(2, gap="large")
 
with col_cv:
    with st.container(border=True):
        step_header(1, "Votre CV", "Un fichier PDF avec du texte sélectionnable.")
 
        uploaded_file = st.file_uploader(
            "Importer votre CV",
            type=["pdf"],
        )
 
        if uploaded_file is not None:
            try:
                cv_text = extract_text_from_pdf(uploaded_file)
                st.success("CV importé avec succès.")
 
                with st.expander("Voir le texte extrait du CV"):
                    st.text_area("CV extrait", value=cv_text, height=250)
 
            except Exception as e:
                st.error("Impossible de lire le fichier PDF.")
                st.exception(e)
 
with col_offer:
    with st.container(border=True):
        step_header(2, "L’offre d’emploi", "Collez l’annonce complète pour une analyse précise.")
 
        job_offer = st.text_area(
            "Offre d'emploi",
            height=250,
            placeholder="Collez ici le contenu de l'offre d'emploi...",
        )
 
 
# ---------------------------------------------------
# Étape 3 : Analyse CV / Offre
# ---------------------------------------------------
 
st.write("")
 
if st.button("Analyser mon CV", type="primary"):
 
    if uploaded_file is None:
        st.warning("Veuillez importer un CV au format PDF.")
 
    elif not cv_text:
        st.warning("Aucun texte n'a pu être extrait du CV.")
 
    elif not job_offer.strip():
        st.warning("Veuillez saisir une offre d'emploi.")
 
    else:
        try:
            with st.spinner("Analyse en cours..."):
                response = call_n8n(cv_text, job_offer, [])
 
            if response.ok:
                st.session_state.analysis_data = response.json()
                st.session_state.adapted_cv = None
            else:
                st.error("Erreur lors de l'appel du workflow n8n.")
                st.write(f"Code HTTP : {response.status_code}")
                st.write(response.text)
 
        except requests.exceptions.RequestException as e:
            st.error("Impossible de communiquer avec n8n.")
            st.exception(e)
 
 
# ---------------------------------------------------
# Résultats de comparaison
# ---------------------------------------------------
 
if st.session_state.analysis_data:
 
    data = st.session_state.analysis_data
    matched_keywords = data.get("matched_keywords", [])
    missing_keywords = data.get("missing_keywords", [])
 
    st.write("")
 
    with st.container(border=True):
        step_header(3, "Résultat de l’analyse", "Ce que votre CV couvre déjà, et ce qui manque.")
 
        total = len(matched_keywords) + len(missing_keywords)
        if total:
            score = round(100 * len(matched_keywords) / total)
            st.markdown(
                '<div class="score"><div class="row">'
                '<span class="label">Correspondance avec l’offre</span>'
                f'<span class="value">{score} %</span></div>'
                f'<div class="bar"><div class="fill" style="width:{score}%"></div></div></div>',
                unsafe_allow_html=True,
            )
 
        col_ok, col_ko = st.columns(2, gap="large")
 
        with col_ok:
            st.markdown('<div class="group-title">Mots-clés présents dans le CV</div>', unsafe_allow_html=True)
            if matched_keywords:
                render_chips(matched_keywords, "ok", "✓")
            else:
                st.markdown('<div class="empty">Aucun mot-clé correspondant.</div>', unsafe_allow_html=True)
 
        with col_ko:
            st.markdown('<div class="group-title">Mots-clés absents du CV</div>', unsafe_allow_html=True)
            if missing_keywords:
                render_chips(missing_keywords, "ko", "✗")
            else:
                st.markdown(
                    '<div class="empty">Aucun mot-clé important n’est absent.</div>',
                    unsafe_allow_html=True,
                )
 
    st.write("")
 
    # ------------------------------------------------
    # Étape 4 : Confirmation + génération
    # ------------------------------------------------
 
    with st.container(border=True):
        confirmed_skills = []
 
        if missing_keywords:
            step_header(
                4,
                "Compétences à confirmer",
                "Cochez uniquement les compétences que vous maîtrisez réellement.",
            )
 
            checks = st.columns(2, gap="large")
            for i, skill in enumerate(missing_keywords):
                with checks[i % 2]:
                    if st.checkbox(f"Je maîtrise : {skill}", key=f"skill_{skill}"):
                        confirmed_skills.append(skill)
        else:
            step_header(
                4,
                "Génération du CV",
                "Aucune compétence à confirmer : vous pouvez générer directement.",
            )
 
        st.write("")
 
        if st.button("Générer le CV personnalisé", type="primary", key="generate_cv"):
            try:
                with st.spinner("Génération du CV personnalisé..."):
                    response = call_n8n(cv_text, job_offer, confirmed_skills)
 
                if response.ok:
                    final_data = response.json()
                    st.session_state.adapted_cv = final_data.get("adapted_cv")
 
                    # Met à jour les listes si n8n les renvoie
                    if "matched_keywords" in final_data or "missing_keywords" in final_data:
                        st.session_state.analysis_data = final_data
                else:
                    st.error("Erreur lors de la génération du CV personnalisé.")
                    st.write(f"Code HTTP : {response.status_code}")
                    st.write(response.text)
 
            except requests.exceptions.RequestException as e:
                st.error("Impossible de communiquer avec n8n.")
                st.exception(e)
 
 
# ---------------------------------------------------
# Étape 5 : CV personnalisé + téléchargement PDF
# ---------------------------------------------------
 
if st.session_state.adapted_cv:
 
    adapted_cv = st.session_state.adapted_cv
 
    st.write("")
 
    with st.container(border=True):
        step_header(5, "Votre CV personnalisé", "Relisez le texte, puis téléchargez-le en PDF.")
 
        st.text_area("Résultat", value=adapted_cv, height=400)
 
        pdf_file = generate_pdf(adapted_cv)
 
        st.download_button(
            label="Télécharger le CV personnalisé en PDF",
            data=pdf_file,
            file_name="CV_personnalise.pdf",
            mime="application/pdf",
        )
 
st.markdown('<div class="foot">CV Personalizer</div>', unsafe_allow_html=True)
 
 