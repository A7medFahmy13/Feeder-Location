import tkinter as tk

# إنشاء نافذة
root = tk.Tk()
root.title("شكرا مهندس موسي")

# ضبط حجم النافذة
root.geometry("300x150")

# إضافة رسالة
label = tk.Label(root, text="انتهى العرض", font=("Arial", 20, "bold"), fg="red")
label.pack(expand=True)

# تشغيل التطبيق
root.mainloop()
