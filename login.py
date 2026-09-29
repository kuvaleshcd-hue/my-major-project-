"""
login.py — Beautiful login / signup page for Sarvam VideoDubber
Uses the existing db.create_user / db.verify_user functions.
"""

import streamlit as st
import db


def _inject_login_css():
    """Inject the full-page login styling."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Hide Streamlit chrome on login page ──────────────────────── */
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stToolbar"] { display: none; }

    /* ── Full-page background ─────────────────────────────────────── */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 40%, #0f172a 100%);
        overflow: hidden;
    }

    /* ── Animated floating shapes ─────────────────────────────────── */
    .login-bg {
        position: fixed; inset: 0; z-index: 0;
        pointer-events: none; overflow: hidden;
    }
    .login-bg .orb {
        position: absolute;
        border-radius: 50%;
        filter: blur(80px);
        animation: orb-float 12s ease-in-out infinite alternate;
    }
    .login-bg .orb-1 {
        width: 420px; height: 420px;
        background: rgba(99, 102, 241, 0.35);
        top: -80px; left: -60px;
    }
    .login-bg .orb-2 {
        width: 500px; height: 500px;
        background: rgba(236, 72, 153, 0.25);
        bottom: -120px; right: -80px;
        animation-delay: -3s;
    }
    .login-bg .orb-3 {
        width: 300px; height: 300px;
        background: rgba(6, 182, 212, 0.25);
        top: 45%; left: 55%;
        animation-delay: -6s;
    }
    @keyframes orb-float {
        0%   { transform: translate(0, 0) scale(1); }
        100% { transform: translate(30px, -40px) scale(1.08); }
    }

    /* ── Glass card ───────────────────────────────────────────────── */
    .glass-card {
        background: rgba(30, 41, 59, 0.55);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 48px 40px 40px;
        max-width: 440px;
        margin: 0 auto;
        box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.5);
        animation: card-up 0.7s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        z-index: 1;
    }
    @keyframes card-up {
        0%   { opacity: 0; transform: translateY(30px); }
        100% { opacity: 1; transform: translateY(0); }
    }

    /* ── Brand header ─────────────────────────────────────────────── */
    .login-brand {
        text-align: center;
        margin-bottom: 8px;
    }
    .login-brand .logo {
        font-size: 44px;
        margin-bottom: 4px;
    }
    .login-brand h2 {
        font-family: 'Inter', sans-serif;
        font-size: 26px;
        font-weight: 700;
        background: linear-gradient(to right, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 4px;
    }
    .login-brand p {
        font-size: 14px;
        color: #94a3b8;
        margin: 0;
    }

    /* ── Divider ──────────────────────────────────────────────────── */
    .login-divider {
        display: flex; align-items: center;
        margin: 20px 0 16px;
        color: #64748b; font-size: 13px;
    }
    .login-divider::before,
    .login-divider::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .login-divider span { padding: 0 12px; }

    /* ── Streamlit input overrides (dark theme) ───────────────────── */
    .glass-card input[type="text"],
    .glass-card input[type="password"],
    .glass-card input[type="email"],
    div[data-testid="stTextInput"] input {
        background: rgba(15, 23, 42, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #fff !important;
        padding: 12px 16px !important;
        font-size: 15px !important;
        transition: border-color 0.25s, box-shadow 0.25s !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
    }
    div[data-testid="stTextInput"] label {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }

    /* ── Primary button ───────────────────────────────────────────── */
    .glass-card button[kind="primary"],
    div[data-testid="stButton"] button[kind="primary"] {
        background: #6366f1 !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
        width: 100% !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background: #4f46e5 !important;
        box-shadow: 0 10px 25px -8px rgba(99, 102, 241, 0.45) !important;
        transform: translateY(-1px);
    }

    /* ── Secondary / link button ──────────────────────────────────── */
    div[data-testid="stButton"] button[kind="secondary"] {
        background: transparent !important;
        color: #6366f1 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        transition: all 0.2s !important;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.04) !important;
        border-color: rgba(255,255,255,0.2) !important;
    }

    /* ── Toggle text link ─────────────────────────────────────────── */
    .toggle-link {
        text-align: center;
        font-size: 14px;
        color: #94a3b8;
        margin-top: 24px;
    }
    .toggle-link a, .toggle-link span.link {
        color: #6366f1;
        font-weight: 500;
        cursor: pointer;
        text-decoration: none;
    }
    .toggle-link a:hover, .toggle-link span.link:hover {
        color: #818cf8;
        text-decoration: underline;
    }

    /* ── Alerts ────────────────────────────────────────────────────── */
    div[data-testid="stAlert"] {
        border-radius: 12px !important;
        font-size: 14px !important;
    }

    /* ── Footer ────────────────────────────────────────────────────── */
    .login-footer {
        text-align: center;
        font-size: 12px;
        color: #475569;
        margin-top: 24px;
    }
    </style>
    """, unsafe_allow_html=True)


def _render_background():
    """Render the animated gradient background orbs."""
    st.markdown("""
    <div class="login-bg">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
    </div>
    """, unsafe_allow_html=True)


def show_login_page():
    """
    Display a premium login / signup page.
    Returns True when the user is authenticated, False otherwise.
    Sets st.session_state["authenticated"] and st.session_state["username"].
    """
    # Already logged in?
    if st.session_state.get("authenticated"):
        return True

    _inject_login_css()
    _render_background()

    # Track which form to show
    if "login_mode" not in st.session_state:
        st.session_state["login_mode"] = "login"

    # ── Centered card container ──────────────────────────────────────
    _, center, _ = st.columns([1, 1.3, 1])

    with center:
        st.markdown("""
        <div class="glass-card">
            <div class="login-brand">
                <div class="logo">🎙️</div>
                <h2>{title}</h2>
                <p>{subtitle}</p>
            </div>
        </div>
        """.format(
            title="Welcome Back" if st.session_state["login_mode"] == "login" else "Create Account",
            subtitle="Sign in to continue dubbing videos"
            if st.session_state["login_mode"] == "login"
            else "Get started with Sarvam VideoDubber",
        ), unsafe_allow_html=True)

        # ── Form ─────────────────────────────────────────────────
        if st.session_state["login_mode"] == "login":
            _login_form()
        else:
            _signup_form()

    return st.session_state.get("authenticated", False)


def _login_form():
    """Render the sign-in form."""
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Enter your username", key="login_user")
        password = st.text_input("Password", placeholder="Enter your password", type="password", key="login_pass")

        submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

    if submitted:
        if not username or not password:
            st.error("Please fill in all fields.")
        elif db.verify_user(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Invalid username or password.")

    # Toggle to signup
    st.markdown("")
    if st.button("Don't have an account? **Sign up**", use_container_width=True, type="secondary", key="go_signup"):
        st.session_state["login_mode"] = "signup"
        st.rerun()

    st.markdown('<div class="login-footer">⚡ Powered by Sarvam AI</div>', unsafe_allow_html=True)


def _signup_form():
    """Render the sign-up form."""
    with st.form("signup_form", clear_on_submit=False):
        new_user = st.text_input("Username", placeholder="Choose a username", key="signup_user")
        new_pass = st.text_input("Password", placeholder="Create a password", type="password", key="signup_pass")
        confirm  = st.text_input("Confirm Password", placeholder="Re-enter password", type="password", key="signup_confirm")

        submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

    if submitted:
        if not new_user or not new_pass or not confirm:
            st.error("Please fill in all fields.")
        elif new_pass != confirm:
            st.error("❌ Passwords do not match.")
        elif len(new_pass) < 4:
            st.warning("Password must be at least 4 characters.")
        elif db.create_user(new_user, new_pass):
            st.success("✅ Account created! You can now sign in.")
            st.session_state["login_mode"] = "login"
            st.rerun()
        else:
            st.error("❌ Username already exists. Choose a different one.")

    # Toggle to login
    st.markdown("")
    if st.button("Already have an account? **Sign in**", use_container_width=True, type="secondary", key="go_login"):
        st.session_state["login_mode"] = "login"
        st.rerun()

    st.markdown('<div class="login-footer">⚡ Powered by Sarvam AI</div>', unsafe_allow_html=True)
