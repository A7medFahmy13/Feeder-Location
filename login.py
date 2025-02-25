import streamlit as st
import pandas as pd
import hashlib
import time

@st.cache_resource
def load_users():
    file_path = "users.xlsx"
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip().str.lower()
        
        required_columns = {"username", "password", "role", "linked_name"}
        if not required_columns.issubset(df.columns):
            st.error("❌ خطأ: ملف المستخدمين غير مكتمل!")
            return {}, {}, {}
        
        df["username"] = df["username"].str.strip().str.lower()
        df["password"] = df["password"].apply(lambda x: hashlib.sha256(str(x).encode()).hexdigest())
        df["role"] = df["role"].str.strip().str.lower()
        df["linked_name"] = df["linked_name"].str.strip().str.lower().replace(" ", "_")
        
        return df.set_index("username")["password"].to_dict(), df.set_index("username")["role"].to_dict(), df.set_index("username")["linked_name"].to_dict()
    except Exception as e:
        st.error(f"⚠️ خطأ: {e}")
        return {}, {}, {}

USERS, USER_ROLES, USER_LINKED_NAMES = load_users()

def authenticate(username, password):
    username, password = username.strip().lower(), hashlib.sha256(password.strip().encode()).hexdigest()
    return USERS.get(username) == password

def login_page():
    st.set_page_config(page_title="تسجيل الدخول", page_icon="🔑", layout="centered")
    st.image("login_banner.png", width=250)
    st.markdown("<h1 style='text-align: center;'>🚀 تسجيل الدخول</h1>", unsafe_allow_html=True)

    username = st.text_input("👤 اسم المستخدم").strip().lower()
    password = st.text_input("🔑 كلمة المرور", type="password").strip()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚪 تسجيل الدخول"):
            with st.spinner("🔄 جارٍ التحقق..."):
                time.sleep(1)
                if authenticate(username, password):
                    st.session_state.update({
                        "authenticated": True,
                        "user": username,
                        "role": USER_ROLES.get(username, "unknown"),
                        "linked_name": USER_LINKED_NAMES.get(username, "unknown")
                    })
                    st.success("✅ تم تسجيل الدخول بنجاح!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة!")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>🔒 جميع البيانات مشفرة للحفاظ على الأمان</p>", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login_page()
    st.stop()
