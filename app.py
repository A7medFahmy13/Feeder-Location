import streamlit as st

# إعداد الصفحة
st.set_page_config(page_title="العرض انتهى", page_icon="✅", layout="centered")

# عنوان الصفحة
st.title("🎬 انتهى العرض")

# نص الإنهاء
st.markdown("""
## شكرًا لمشاهدتك العرض! 🎉
نتمنى أن يكون قد نال إعجابك.
""")

# زر لإنهاء العرض أو العودة
if st.button("🔄 إعادة التشغيل"):
    st.experimental_rerun()
