"""ClipGenesis — Sunset 🔥 Orange/Red dark-mode UI shell — CSS, sidebar, KPI cards, floating preview."""

import streamlit as st

PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
  --cg-bg:            #0D0D0D;
  --cg-surface:       #161616;
  --cg-surface2:      #1E1E1E;
  --cg-surface3:      #252525;
  --cg-accent:        #FF6B35;
  --cg-accent2:       #FF4500;
  --cg-accent3:       #FFB347;
  --cg-accent-glow:   rgba(255,107,53,0.22);
  --cg-accent-glow2:  rgba(255,69,0,0.15);
  --cg-success:       #00E5A0;
  --cg-warning:       #FFB347;
  --cg-danger:        #FF3B5C;
  --cg-text:          #F5F0EB;
  --cg-muted:         #8A7F78;
  --cg-border:        #2A2420;
  --cg-border-hot:    rgba(255,107,53,0.4);
  --cg-radius:        14px;
  --cg-radius-sm:     8px;
}

/* ── Global ─────────────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
  background-color: var(--cg-bg) !important;
  color: var(--cg-text) !important;
}

.main .block-container {
  padding-top: 1.5rem;
  padding-bottom: 2rem;
  max-width: 1400px;
}

/* ── Sidebar ─────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #111111 0%, #0D0D0D 60%, #100A06 100%);
  border-right: 1px solid var(--cg-border-hot);
}

section[data-testid="stSidebar"]::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, #FF4500, #FF6B35, #FFB347);
}

/* ── Sidebar: ALL text elements forced bright ────────────────── */
section[data-testid="stSidebar"] * {
  opacity: 1 !important;
}

/* every possible radio label selector across Streamlit versions */
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] div[role="radiogroup"] label,
section[data-testid="stSidebar"] div[data-testid="stRadio"] label,
section[data-testid="stSidebar"] .stRadio div label {
  padding: 10px 16px;
  border-radius: var(--cg-radius-sm);
  transition: all 0.25s ease;
  margin-bottom: 3px;
  color: #D8CFC8 !important;
  font-size: 0.9rem;
  opacity: 1 !important;
}

/* all text nodes inside sidebar radio buttons */
section[data-testid="stSidebar"] .stRadio label *,
section[data-testid="stSidebar"] div[role="radiogroup"] label *,
section[data-testid="stSidebar"] div[role="radiogroup"] p,
section[data-testid="stSidebar"] div[role="radiogroup"] span,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span {
  color: #D8CFC8 !important;
  opacity: 1 !important;
}

/* hover state */
section[data-testid="stSidebar"] .stRadio label:hover,
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
  background: rgba(255,107,53,0.12) !important;
  color: #FFFFFF !important;
}

section[data-testid="stSidebar"] .stRadio label:hover *,
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover * {
  color: #FFFFFF !important;
}

/* active / selected item */
section[data-testid="stSidebar"] .stRadio [aria-checked="true"],
section[data-testid="stSidebar"] div[role="radiogroup"] [aria-checked="true"] {
  background: linear-gradient(90deg, rgba(255,107,53,0.25), rgba(255,69,0,0.12)) !important;
  border-left: 3px solid #FF6B35 !important;
  color: #FFFFFF !important;
  font-weight: 600;
  box-shadow: inset 0 0 20px rgba(255,107,53,0.1);
}

section[data-testid="stSidebar"] .stRadio [aria-checked="true"] *,
section[data-testid="stSidebar"] div[role="radiogroup"] [aria-checked="true"] * {
  color: #FFFFFF !important;
}

/* general sidebar paragraph / span text (version-safe) */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
  color: #D8CFC8;  /* no !important — lets selected/hover override */
}


/* ── ALL Section Headings & Container Titles (h1-h6) ────────────────────────── */
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6,
div[data-testid="stVerticalBlockBorderWrapper"] h1,
div[data-testid="stVerticalBlockBorderWrapper"] h2,
div[data-testid="stVerticalBlockBorderWrapper"] h3,
div[data-testid="stVerticalBlockBorderWrapper"] h4,
div[data-testid="stVerticalBlockBorderWrapper"] h5,
div[data-testid="stVerticalBlockBorderWrapper"] h6 {
  color: #FFD700 !important; /* Vivid Gold/Yellow */
  font-weight: 800 !important;
  font-size: 1.35rem !important;
  letter-spacing: 0.5px !important;
  opacity: 1 !important;
  text-shadow: 0 2px 10px rgba(0,0,0,0.9), 0 0 12px rgba(255,215,0,0.3) !important;
  margin-bottom: 0.75rem !important;
}

/* Gradient Accent Effect for Subheadings (#### Titles like Quran Input, Video Settings) */
[data-testid="stMarkdownContainer"] h4,
div[data-testid="stVerticalBlockBorderWrapper"] h4 {
  background: linear-gradient(135deg, #FFD700 0%, #00E5A0 50%, #FF6B35 100%) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
  display: inline-block !important;
  font-size: 1.4rem !important;
  font-weight: 800 !important;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.9)) !important;
}

/* ── Container Border Box Glow & Clarity ─────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(180deg, #181818 0%, #121212 100%) !important;
  border: 1px solid rgba(255, 107, 53, 0.45) !important;
  border-radius: 14px !important;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5), inset 0 0 15px rgba(255,107,53,0.06) !important;
  padding: 16px !important;
}

/* ── All Widget Labels (globally) ────────────────────────────── */
label,
.stTextInput > label,
.stTextArea > label,
.stSelectbox > label,
.stMultiSelect > label,
.stSlider > label,
.stCheckbox > label,
.stRadio > label,
.stColorPicker > label,
.stFileUploader > label,
.stNumberInput > label,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span {
  color: #F5EBE6 !important;
  font-weight: 600 !important;
  font-size: 0.95rem !important;
  opacity: 1 !important;
}

/* ── st.write() / st.markdown() text ────────────────────────── */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] em {
  color: #E8E0D8 !important;
  opacity: 1 !important;
}

/* ── Text inside bordered containers ────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p,
div[data-testid="stVerticalBlockBorderWrapper"] label {
  color: #E8E0D8 !important;
  opacity: 1 !important;
}

/* ── Checkbox & Radio option text ────────────────────────────── */
.stCheckbox label p,
.stCheckbox label span,
.stRadio label p,
.stRadio label span {
  color: #E8E0D8 !important;
  opacity: 1 !important;
}

/* ── Selectbox displayed value ───────────────────────────────── */
[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSelectbox"] span {
  color: #F5F0EB !important;
  opacity: 1 !important;
}

/* ── Metric labels & values ──────────────────────────────────── */
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p {
  color: #C8BFB8 !important;
  opacity: 1 !important;
}
[data-testid="stMetricValue"] {
  color: #FF6B35 !important;
  font-weight: 700 !important;
}

/* ── Caption / small helper text ─────────────────────────────── */
[data-testid="stCaptionContainer"] p,
.stCaption { color: #9A8F88 !important; opacity: 1 !important; }

/* ── Alert / info box text ───────────────────────────────────── */
.stAlert p, .stAlert span, .stAlert strong {
  color: #F5F0EB !important;
  opacity: 1 !important;
}

/* ── Expander text ───────────────────────────────────────────── */
.streamlit-expanderHeader p,
.streamlit-expanderHeader span {
  color: #F5F0EB !important;
  opacity: 1 !important;
}

/* ── Input placeholder ───────────────────────────────────────── */
::placeholder { color: #5A504A !important; opacity: 1 !important; }

/* ── KPI Cards ───────────────────────────────────────────────── */
.kpi-card {
  background: linear-gradient(135deg, var(--cg-surface) 0%, var(--cg-surface2) 100%);
  border: 1px solid var(--cg-border-hot);
  border-radius: var(--cg-radius);
  padding: 24px 20px;
  text-align: center;
  position: relative;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, #FF4500, #FF6B35, #FFB347);
}

.kpi-card::after {
  content: '';
  position: absolute;
  bottom: -30px; right: -30px;
  width: 80px; height: 80px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,107,53,0.12) 0%, transparent 70%);
}

.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(255,69,0,0.25), 0 0 0 1px var(--cg-border-hot);
}

.kpi-value {
  font-size: 2.2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #FF6B35, #FFB347);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.1;
  letter-spacing: -1px;
}

.kpi-label {
  font-size: 0.78rem;
  color: var(--cg-muted);
  margin-top: 6px;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 500;
}

.kpi-delta { font-size: 0.8rem; margin-top: 8px; font-weight: 500; }
.kpi-delta.up   { color: var(--cg-success); }
.kpi-delta.down { color: var(--cg-danger); }

/* ── Page Title ──────────────────────────────────────────────── */
.page-title {
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #FF6B35 0%, #FFB347 50%, #FF4500 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 4px;
  letter-spacing: -0.5px;
}

.page-subtitle {
  font-size: 0.95rem;
  color: var(--cg-muted);
  margin-bottom: 24px;
}

/* ── Wizard Bar ──────────────────────────────────────────────── */
.wizard-bar {
  display: flex;
  justify-content: center;
  gap: 0;
  margin-bottom: 28px;
  padding: 0 8px;
}

.wizard-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--cg-surface);
  border: 1px solid var(--cg-border);
  font-size: 0.85rem;
  color: var(--cg-muted);
  transition: all 0.3s ease;
}

.wizard-step:first-child { border-radius: 10px 0 0 10px; }
.wizard-step:last-child  { border-radius: 0 10px 10px 0; }

.wizard-step.active {
  background: linear-gradient(135deg, rgba(255,107,53,0.2), rgba(255,69,0,0.1));
  border-color: var(--cg-accent);
  color: var(--cg-text);
  font-weight: 600;
  box-shadow: 0 0 20px rgba(255,107,53,0.2);
}

.wizard-step.done {
  color: var(--cg-success);
  border-color: rgba(0,229,160,0.4);
}

.wizard-num {
  width: 24px; height: 24px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  background: var(--cg-surface2);
  border: 1px solid var(--cg-border);
}

.wizard-step.active .wizard-num {
  background: linear-gradient(135deg, #FF4500, #FF6B35);
  border-color: #FF6B35;
  color: #fff;
  box-shadow: 0 0 10px rgba(255,107,53,0.5);
}

.wizard-step.done .wizard-num {
  background: var(--cg-success);
  border-color: var(--cg-success);
  color: #fff;
}

.wizard-arrow {
  color: var(--cg-muted);
  font-size: 1rem;
  display: flex;
  align-items: center;
  padding: 0 2px;
}

/* ── Floating Preview ────────────────────────────────────────── */
.float-preview {
  position: fixed;
  bottom: 24px; right: 24px;
  width: 360px; max-height: 300px;
  background: var(--cg-surface);
  border: 1px solid var(--cg-border-hot);
  border-radius: var(--cg-radius);
  box-shadow: 0 16px 48px rgba(255,69,0,0.25), 0 0 0 1px var(--cg-border-hot);
  z-index: 9999;
  overflow: hidden;
}

.float-preview-header {
  background: linear-gradient(90deg, #FF4500, #FF6B35);
  padding: 10px 16px;
  font-weight: 600;
  font-size: 0.85rem;
  color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.float-preview-body { padding: 8px; max-height: 240px; overflow-y: auto; }

/* ── Tabs ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
  background: var(--cg-surface);
  border-radius: 10px;
  padding: 4px;
  border: 1px solid var(--cg-border);
}

.stTabs [data-baseweb="tab"] {
  border-radius: 8px;
  padding: 8px 20px;
  font-weight: 500;
  color: var(--cg-muted) !important;
}

.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(255,107,53,0.25), rgba(255,69,0,0.15)) !important;
  color: var(--cg-text) !important;
  border: 1px solid var(--cg-border-hot) !important;
}

/* ── Buttons ─────────────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stDownloadButton > button {
  background: linear-gradient(135deg, #FF4500 0%, #FF6B35 50%, #FF8C42 100%) !important;
  border: none !important;
  border-radius: var(--cg-radius-sm) !important;
  font-weight: 600 !important;
  color: #fff !important;
  box-shadow: 0 4px 16px rgba(255,69,0,0.35) !important;
  transition: all 0.2s ease !important;
  letter-spacing: 0.3px;
}

.stButton > button[kind="primary"]:hover {
  box-shadow: 0 8px 24px rgba(255,69,0,0.5) !important;
  transform: translateY(-2px) !important;
}

.stButton > button[kind="secondary"] {
  border: 1px solid var(--cg-border-hot) !important;
  color: var(--cg-accent) !important;
  border-radius: var(--cg-radius-sm) !important;
  background: transparent !important;
  transition: all 0.2s ease !important;
}

.stButton > button[kind="secondary"]:hover {
  background: var(--cg-accent-glow) !important;
}

/* ── Containers / Cards ──────────────────────────────────────── */
.stContainer,
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--cg-border-hot) !important;
  border-radius: var(--cg-radius) !important;
  background: var(--cg-surface) !important;
}

/* ── Headings ────────────────────────────────────────────────── */
h1 {
  background: linear-gradient(135deg, #FF6B35, #FFB347);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 800 !important;
}

h2, h3 { color: var(--cg-text) !important; font-weight: 700 !important; }

.streamlit-expanderHeader { font-weight: 600 !important; color: var(--cg-text) !important; }

/* ── Metrics ─────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--cg-surface);
  border: 1px solid var(--cg-border-hot);
  border-radius: var(--cg-radius-sm);
  padding: 12px 16px !important;
}

[data-testid="stMetricValue"] {
  color: var(--cg-accent) !important;
  font-weight: 700 !important;
}

[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }
/* ── Global 100% Full Screen (Zero Whitespace & Margin Removal) ────── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp {
  background-color: #0D0D0D !important;
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
}

header[data-testid="stHeader"],
div[data-testid="stDecoration"],
div[data-testid="stToolbar"],
[data-testid="stHeader"] {
  display: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  visibility: hidden !important;
}

.main, section.main {
  background-color: #0D0D0D !important;
  padding: 0 !important;
  margin: 0 !important;
  width: 100% !important;
}

.main .block-container,
[data-testid="stMainBlockContainer"] {
  padding-top: 0.2rem !important;
  padding-bottom: 0.5rem !important;
  padding-left: 0.5rem !important;
  padding-right: 0.5rem !important;
  max-width: 100% !important;
  width: 100% !important;
  margin: 0 !important;
}

/* ── Hide Streamlit Sidebar ───────────────────────────────────── */
section[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
button[kind="header"] {
  display: none !important;
}

/* ── Top Horizontal Navigation Tabs (Full Width 3D Colorful Buttons) ── */
div[data-testid="stRadio"] div[role="radiogroup"] {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: wrap !important;
  gap: 8px !important;
  justify-content: space-between !important;
  background: #141414 !important;
  padding: 10px 12px !important;
  border-radius: 14px !important;
  border: 1px solid rgba(255, 107, 53, 0.45) !important;
  box-shadow: 0 4px 20px rgba(0,0,0,0.6), inset 0 0 15px rgba(255,107,53,0.08) !important;
  margin-bottom: 14px !important;
  width: 100% !important;
}

/* Completely Hide Radio Circle Dots */
div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child,
div[data-testid="stRadio"] div[role="radiogroup"] label div[role="radio"],
div[data-testid="stRadio"] div[role="radiogroup"] label input,
div[data-testid="stRadio"] div[role="radiogroup"] label svg,
div[data-testid="stRadio"] div[role="radiogroup"] label [data-testid="stRadioDot"] {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
  opacity: 0 !important;
  visibility: hidden !important;
}

/* 3D Button Style for Every Navigation Tab */
div[data-testid="stRadio"] div[role="radiogroup"] label {
  position: relative !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 10px 16px !important;
  border-radius: 10px !important;
  font-weight: 800 !important;
  font-size: 0.9rem !important;
  cursor: pointer !important;
  text-shadow: 0 1px 3px rgba(0,0,0,0.9) !important;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
  border: 1px solid rgba(255,255,255,0.3) !important;
  margin: 0 !important;
  flex: 1 1 auto !important;
  min-width: 120px !important;
  text-align: center !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] label * {
  color: #FFFFFF !important;
  font-weight: 800 !important;
  font-size: 0.9rem !important;
  opacity: 1 !important;
  text-shadow: 0 1px 3px rgba(0,0,0,0.9) !important;
}

/* Hover Effect */
div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
  filter: brightness(1.25) !important;
  transform: translateY(-2px) !important;
}

/* ── Page Title & Subtitle (Collapsing Big Titles) ─────────────── */
.page-title, .page-subtitle {
  display: none !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* 1. Dashboard - Vivid Emerald Green */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(1),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(1) {
  background: linear-gradient(180deg, #10B981 0%, #059669 100%) !important;
  box-shadow: 0 5px 0 #046C4E, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 2. Quran Video - Golden Amber */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(2),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(2) {
  background: linear-gradient(180deg, #F59E0B 0%, #D97706 100%) !important;
  box-shadow: 0 5px 0 #92400E, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 3. Darood Shareef - Islamic Teal Emerald */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(3),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(3) {
  background: linear-gradient(180deg, #14B8A6 0%, #0D9488 100%) !important;
  box-shadow: 0 5px 0 #115E59, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 4. Link Re-Creator - Cyber Neon Lime Cyan */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(4),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(4) {
  background: linear-gradient(180deg, #06B6D4 0%, #0284C7 100%) !important;
  box-shadow: 0 5px 0 #0369A1, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 5. PK Urdu Video - Ruby Crimson */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(5),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(5) {
  background: linear-gradient(180deg, #F43F5E 0%, #E11D48 100%) !important;
  box-shadow: 0 5px 0 #9F1239, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 6. Single Video - Cyber Sapphire Blue */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(6),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(6) {
  background: linear-gradient(180deg, #3B82F6 0%, #2563EB 100%) !important;
  box-shadow: 0 5px 0 #1E40AF, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 7. Batch Gen - Deep Electric Purple */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(7),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(7) {
  background: linear-gradient(180deg, #8B5CF6 0%, #7C3AED 100%) !important;
  box-shadow: 0 5px 0 #5B21B6, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 8. Video Wizard - Flame Orange */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(8),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(8) {
  background: linear-gradient(180deg, #FF6B35 0%, #FF4500 100%) !important;
  box-shadow: 0 5px 0 #B33000, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 9. Voice Studio - Neon Pink */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(9),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(9) {
  background: linear-gradient(180deg, #EC4899 0%, #DB2777 100%) !important;
  box-shadow: 0 5px 0 #9D174D, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 10. Voice & Trends - Sunflower Gold */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(10),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(10) {
  background: linear-gradient(180deg, #EAB308 0%, #CA8A04 100%) !important;
  box-shadow: 0 5px 0 #854D0E, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 11. Templates - Royal Indigo */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(11),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(11) {
  background: linear-gradient(180deg, #6366F1 0%, #4F46E5 100%) !important;
  box-shadow: 0 5px 0 #3730A3, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 12. Smart Script - Cyan Turquoise */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(12),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(12) {
  background: linear-gradient(180deg, #06B6D4 0%, #0891B2 100%) !important;
  box-shadow: 0 5px 0 #155E75, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 13. A/B Testing - Coral Sunset */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(13),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(13) {
  background: linear-gradient(180deg, #F97316 0%, #EA580C 100%) !important;
  box-shadow: 0 5px 0 #9A3412, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* 14. Settings - Slate Titanium */
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-child(14),
div[data-testid="stRadio"] div[role="radiogroup"] label:nth-of-type(14) {
  background: linear-gradient(180deg, #64748B 0%, #475569 100%) !important;
  box-shadow: 0 5px 0 #1E293B, 0 6px 12px rgba(0,0,0,0.5) !important;
}

/* ── Active Tab Radium Light Blinking Pulse Animation (MUST OVERRIDE ALL NTH-CHILD RULES) ────────────────────────── */
@keyframes radium-light-blink {
  0%, 100% {
    background: linear-gradient(180deg, #39FF14 0%, #00FF66 100%) !important;
    box-shadow: 0 0 25px #39FF14, 0 0 50px rgba(57, 255, 20, 0.95), inset 0 0 12px #FFFFFF !important;
    border-color: #CCFF00 !important;
    transform: translateY(-2px) scale(1.04) !important;
    filter: brightness(1.3) !important;
  }
  50% {
    background: linear-gradient(180deg, #00FF66 0%, #00E5A0 100%) !important;
    box-shadow: 0 0 10px #39FF14, 0 0 20px rgba(57, 255, 20, 0.6), inset 0 0 6px #FFFFFF !important;
    border-color: #00FF66 !important;
    transform: translateY(0px) scale(1.0) !important;
    filter: brightness(1.05) !important;
  }
}

/* Active Selected Tab: Radium Green Background + Black Bold Text + Blinking Light */
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked),
div[data-testid="stRadio"] div[role="radiogroup"] label:has([aria-checked="true"]),
div[data-testid="stRadio"] div[role="radiogroup"] label[aria-checked="true"],
div[data-testid="stRadio"] div[role="radiogroup"] [aria-checked="true"] {
  animation: radium-light-blink 1.2s ease-in-out infinite !important;
  background: linear-gradient(180deg, #39FF14 0%, #00FF66 100%) !important;
  border: 2px solid #CCFF00 !important;
  color: #000000 !important;
  font-weight: 900 !important;
  z-index: 10 !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) *,
div[data-testid="stRadio"] div[role="radiogroup"] label:has([aria-checked="true"]) *,
div[data-testid="stRadio"] div[role="radiogroup"] label[aria-checked="true"] *,
div[data-testid="stRadio"] div[role="radiogroup"] [aria-checked="true"] *,
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p,
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) span,
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) div,
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) label {
  color: #000000 !important;
  font-weight: 900 !important;
  text-shadow: none !important;
}

</style>
"""

PAGES = [
    {"icon": "🏠", "label": "Dashboard",     "key": "dashboard"},
    {"icon": "📖", "label": "Quran Video",   "key": "quran"},
    {"icon": "🕌", "label": "Darood Shareef", "key": "darood"},
    {"icon": "🔗", "label": "Link Re-Creator", "key": "link_recreator"},
    {"icon": "🇵🇰", "label": "Urdu Video",   "key": "urdu"},
    {"icon": "📺", "label": "Single Video",  "key": "single"},
    {"icon": "📦", "label": "Batch Gen",     "key": "batch"},
    {"icon": "✨", "label": "Video Wizard",  "key": "wizard"},
    {"icon": "🎛️", "label": "Voice Studio", "key": "voicestudio"},
    {"icon": "🎙️", "label": "Voice & Trends","key": "voice"},
    {"icon": "🎨", "label": "Templates",     "key": "templates"},
    {"icon": "✍️", "label": "Smart Script",  "key": "scripts"},
    {"icon": "🎯", "label": "A/B Testing",   "key": "abtest"},
    {"icon": "⚙️", "label": "Settings",     "key": "settings"},
]


def inject_premium_css():
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)


def render_sidebar(version="1.3.0"):
    # Top Banner Header
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;background:linear-gradient(135deg,#161616 0%,#1E1E1E 100%);border:1px solid rgba(255,107,53,0.35);border-radius:12px;padding:10px 20px;margin-bottom:12px;box-shadow:0 4px 15px rgba(0,0,0,0.4);">'
        f'<div style="display:flex;align-items:center;gap:12px;">'
        f'<div style="font-size:1.6rem;font-weight:800;background:linear-gradient(135deg,#FF4500,#FF6B35,#FFB347);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-0.5px;">⚡ ClipGenesis</div>'
        f'<span style="font-size:0.75rem;font-weight:600;color:#FF6B35;background:rgba(255,107,53,0.15);border:1px solid rgba(255,107,53,0.3);border-radius:20px;padding:2px 10px;">v{version} — AI Video Studio</span>'
        f'</div>'
        f'<div style="font-size:0.85rem;color:#8A7F78;">'
        f'<a href="https://github.com/sahilali2550/ClipGenesis-ai-studio.git" target="_blank" style="color:#FF6B35;text-decoration:none;font-weight:600;">⬡ GitHub Repository</a>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    page_options = [f"{p['icon']} {p['label']}" for p in PAGES]
    curr_idx = st.session_state.get("nav_idx", 0)
    if curr_idx >= len(page_options):
        curr_idx = 0

    if "top_nav_radio" in st.session_state and st.session_state["top_nav_radio"] not in page_options:
        del st.session_state["top_nav_radio"]

    st.markdown('<div class="top-nav-bar">', unsafe_allow_html=True)
    selected = st.radio(
        "TopNavigation",
        options=page_options,
        index=curr_idx,
        horizontal=True,
        label_visibility="collapsed",
        key="top_nav_radio",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.session_state["nav_idx"] = page_options.index(selected)
    return PAGES[st.session_state["nav_idx"]]["key"]


def render_kpi_cards(metrics):
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        delta_html = ""
        if m.get("delta"):
            d = m.get("delta_dir", "up")
            arrow = "▲" if d == "up" else "▼"
            delta_html = f'<div class="kpi-delta {d}">{arrow} {m["delta"]}</div>'
        with col:
            st.markdown(
                f'<div class="kpi-card">'
                f'<div class="kpi-value">{m["value"]}</div>'
                f'<div class="kpi-label">{m["label"]}</div>'
                f'{delta_html}</div>',
                unsafe_allow_html=True,
            )


def render_wizard_bar(steps, current):
    html = '<div class="wizard-bar">'
    for i, step in enumerate(steps):
        cls = "active" if i == current else ("done" if i < current else "")
        mark = "✓" if i < current else str(i + 1)
        html += (
            f'<div class="wizard-step {cls}">'
            f'<span class="wizard-num">{mark}</span><span>{step}</span></div>'
        )
        if i < len(steps) - 1:
            html += '<span class="wizard-arrow">→</span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_floating_preview(video_path=None, audio_path=None, title="Preview"):
    if not video_path and not audio_path:
        return
    body = ""
    if video_path:
        body += (
            f'<div style="padding:8px;"><video controls style="width:100%;border-radius:8px;max-height:180px;">'
            f'<source src="file://{video_path}" type="video/mp4"></video></div>'
        )
    if audio_path:
        body += (
            f'<div style="padding:8px;"><audio controls style="width:100%;">'
            f'<source src="file://{audio_path}" type="audio/mpeg"></audio></div>'
        )
    html = (
        '<div class="float-preview">'
        f'<div class="float-preview-header"><span>🔥 {title}</span></div>'
        f'<div class="float-preview-body">{body}</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_floating_preview_button():
    if "show_preview" not in st.session_state:
        st.session_state["show_preview"] = False
    if st.session_state.get("preview_video") or st.session_state.get("preview_audio"):
        label = "🔥 Toggle Preview" if not st.session_state["show_preview"] else "✕ Hide Preview"
        if st.button(label, key="toggle_preview_btn"):
            st.session_state["show_preview"] = not st.session_state["show_preview"]
            st.rerun()
        if st.session_state["show_preview"]:
            render_floating_preview(
                video_path=st.session_state.get("preview_video"),
                audio_path=st.session_state.get("preview_audio"),
                title=st.session_state.get("preview_title", "Preview"),
            )


def render_logo_watermark_uploader(key_prefix="global"):
    """
    Render a reusable Channel Logo Watermark uploader widget across all video generation pages.
    Returns: (logo_path, logo_position, logo_size, logo_opacity)
    """
    import os
    from app.utils import utils

    with st.container(border=True):
        st.markdown("#### 🏷️ Channel Logo Watermark")
        logo_file = st.file_uploader(
            "Upload Channel Logo / Watermark PNG (Optional)",
            type=["png", "jpg", "jpeg"],
            key=f"{key_prefix}_logo_upload",
            help="Upload your channel logo to automatically overlay it as a watermark on the generated video."
        )

        logo_path = ""
        if logo_file is not None:
            temp_logo_dir = os.path.join(utils.root_dir(), "storage", "logos")
            os.makedirs(temp_logo_dir, exist_ok=True)
            logo_path = os.path.join(temp_logo_dir, logo_file.name)
            with open(logo_path, "wb") as f:
                f.write(logo_file.getbuffer())
            st.success(f"🏷️ Channel Logo Loaded: **{logo_file.name}**")

        if logo_path:
            c1, c2, c3 = st.columns(3)
            with c1:
                logo_pos = st.selectbox(
                    "Position",
                    options=["top_right", "top_left", "top_center", "bottom_right", "bottom_left"],
                    format_func=lambda x: {
                        "top_right": "↗️ Top Right",
                        "top_left": "↖️ Top Left",
                        "top_center": "⏺️ Top Center",
                        "bottom_right": "↘️ Bottom Right",
                        "bottom_left": "↙️ Bottom Left",
                    }.get(x, x),
                    key=f"{key_prefix}_logo_pos_select"
                )
            with c2:
                logo_sz = st.slider("Width (px)", 60, 300, 130, 10, key=f"{key_prefix}_logo_sz_slider")
            with c3:
                logo_op = st.slider("Opacity", 0.2, 1.0, 0.90, 0.05, key=f"{key_prefix}_logo_op_slider")
        else:
            logo_pos = "top_right"
            logo_sz = 130
            logo_op = 0.90

        return logo_path, logo_pos, logo_sz, logo_op