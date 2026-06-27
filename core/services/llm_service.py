# import requests
# import json
# import sys

# class LLMService:
#     """سرویس ارتباط با Ollama"""
    
#     def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
#         self.base_url = base_url
#         self.model = model
#         self.is_available = self.check_connection()
    
#     def _is_management_command(self) -> bool:
#         """بررسی اینکه آیا در حال اجرای دستور مدیریت هستیم"""
#         management_commands = ['makemigrations', 'migrate', 'createsuperuser', 'shell', 'test', 'check']
#         return any(cmd in sys.argv for cmd in management_commands)
    
#     def check_connection(self) -> bool:
#         try:
#             response = requests.get(f"{self.base_url}/api/tags", timeout=5)
#             if response.status_code == 200:
#                 # فقط در صورتی که دستور مدیریت نباشد پیام چاپ کن
#                 if not self._is_management_command():
#                     print("✅ AI متصل است")
#                 return True
#             return False
#         except:
#             if not self._is_management_command():
#                 print("❌ AI وصل نیست! دستورات: ollama serve && ollama pull llama3.2")
#             return False
    
#     def _call_llm(self, prompt: str) -> str:
#         if not self.is_available:
#             return "AI در دسترس نیست. لطفاً Ollama را اجرا کنید."
        
#         data = {
#             "model": self.model,
#             "prompt": prompt,
#             "stream": False,
#             "options": {"temperature": 0.3, "num_predict": 2048}
#         }
        
#         try:
#             response = requests.post(f"{self.base_url}/api/generate", json=data, timeout=60)
#             if response.status_code == 200:
#                 return response.json().get("response", "")
#             return f"خطا: {response.status_code}"
#         except Exception as e:
#             return f"خطا در ارتباط: {e}"
    
#     def summarize_file(self, content: str, filename: str, detail_level: str = "summary") -> dict:
#         prompts = {
#             "summary": f"""
# فایل "{filename}" را تحلیل کن. فقط مهم‌ترین نکات رو در ۳-۴ خط بنویس.

# محتوا:
# {content[:3000]}

# پاسخ:
# """,
#             "detailed": f"""
# فایل "{filename}" را تحلیل کن و اطلاعات زیر رو بده:

# ۱. عنوان/موضوع اصلی فایل چیست؟
# ۲. اسامی مهم (افراد، شرکت‌ها، مکان‌ها):
# ۳. خلاصه محتوا در ۵ خط:

# محتوا:
# {content[:4000]}

# پاسخ:
# """,
#             "full": f"""
# تحلیل کامل فایل "{filename}":

# محتوا:
# {content[:5000]}

# موارد زیر را بنویس:
# - موضوع اصلی
# - خلاصه کامل
# - نکات کلیدی
# - نتیجه‌گیری
# پاسخ:
# """
#         }
        
#         response = self._call_llm(prompts.get(detail_level, prompts["summary"]))
#         return {"filename": filename, "summary": response, "detail_level": detail_level}
    
#     def scan_file_for_threats(self, content: str, filename: str, file_size: int) -> dict:
#         prompt = f"""
# فایل "{filename}" با حجم {file_size} بایت رو بررسی کن.

# محتوا:
# {content[:3000] if content else "فایل غیر متنی"}

# به این سوالات پاسخ بده (فقط پاسخ کوتاه):
# 1. آیا این فایل مشکوک است؟ (بله/خیر)
# 2. چه نوع خطری دارد؟
# 3. چه اقدامی باید کرد؟

# پاسخ:
# """
#         response = self._call_llm(prompt)
        
#         # پردازش پاسخ
#         is_threat = "بله" in response[:20]
#         threat_type = "unknown"
#         if "ویروس" in response.lower():
#             threat_type = "virus"
#         elif "بدافزار" in response.lower():
#             threat_type = "malware"
#         elif "فیشینگ" in response.lower():
#             threat_type = "phishing"
#         elif "غیرقانونی" in response.lower():
#             threat_type = "illegal"
        
#         return {
#             "is_threat": is_threat,
#             "threat_type": threat_type,
#             "description": response[:300],
#             "recommended_action": "block" if is_threat else "allow",
#             "severity": "high" if is_threat else "low"
#         }
    
#     def answer_question_about_file(self, content: str, filename: str, question: str) -> str:
#         prompt = f"""
# فایل "{filename}" رو بخون و به این سوال پاسخ بده:

# محتوا:
# {content[:4000]}

# سوال: {question}

# پاسخ دقیق و مفید:
# """
#         return self._call_llm(prompt)
    
# def analyze_user_behavior(self, user_data: dict, recent_activities: list) -> str:
#     """تحلیل رفتار کاربر - برگرداندن متن تحلیل"""
#     prompt = f"""
# بر اساس اطلاعات زیر، رفتار کاربر را تحلیل کن و به صورت متن روان فارسی بنویس:

# اطلاعات کاربر:
# - نام کاربری: {user_data.get('username', 'نامشخص')}
# - تعداد فایل‌های آپلود شده: {user_data.get('total_uploads', 0)}
# - نوع فایل‌ها: {user_data.get('file_types', {})}
# - وضعیت: {'ادمین سیستم' if user_data.get('is_staff') else 'کاربر عادی'}
# - تاریخ عضویت: {user_data.get('date_joined', 'نامشخص')}

# لطفاً در پاسخ خود به این موارد بپرداز:
# 1. الگوی رفتاری کاربر چیست؟ (مثلاً: محافظه‌کار، فعال، حرفه‌ای، مبتدی)
# 2. چه نوع فایل‌هایی بیشتر آپلود می‌کند؟
# 3. آیا رفتار مشکوکی در فعالیت‌های او دیده می‌شود؟
# 4. توصیه شما به ادمین برای مدیریت این کاربر چیست؟

# پاسخ خود را به صورت ۳-۴ پاراگراف بنویس:
# """
    
#     response = self._call_llm(prompt)
    
#     # اگر پاسخ خالی یا خیلی کوتاه بود، یک پیام پیش‌فرض برگردان
#     if not response or len(response.strip()) < 20:
#         return f"""
# تحلیل کاربر {user_data.get('username', 'کاربر')}:

# 📊 آمار کلی:
# - تعداد فایل‌ها: {user_data.get('total_uploads', 0)}
# - تنوع فایل‌ها: {len(user_data.get('file_types', {}))} نوع مختلف

# 💡 توصیه: داده‌های کافی برای تحلیل عمیق وجود ندارد. 
# پیشنهاد می‌شود کاربر فعالیت بیشتری داشته باشد تا الگوی رفتاری او مشخص شود.
# """
    
#     return response
# # ایجاد نمونه جهانی با بررسی محیط
# import sys
# _is_management = any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'createsuperuser', 'shell', 'test'])
# if not _is_management:
#     llm_service = LLMService()
# else:
#     llm_service = None




# import requests
# import json
# import sys

# class LLMService:
#     """سرویس ارتباط با Ollama - با مدل gemma3:27b"""
    
#     def __init__(self, base_url: str = "http://localhost:11434", model: str = "gemma3:27b"):
#         self.base_url = base_url
#         self.model = model
#         self.is_available = self.check_connection()
    
#     def _is_management_command(self) -> bool:
#         management_commands = ['makemigrations', 'migrate', 'createsuperuser', 'shell', 'test', 'check']
#         return any(cmd in sys.argv for cmd in management_commands)
    
#     def check_connection(self) -> bool:
#         try:
#             response = requests.get(f"{self.base_url}/api/tags", timeout=10)
#             if response.status_code == 200:
#                 tags = response.json()
#                 models = [tag.get('name') for tag in tags.get('models', [])]
#                 if self.model in models:
#                     if not self._is_management_command():
#                         print(f"✅ AI متصل است - مدل {self.model} آماده است")
#                     return True
#                 else:
#                     if not self._is_management_command():
#                         print(f"⚠️ مدل {self.model} یافت نشد. مدل‌های موجود: {models}")
#                         print(f"برای دانلود مدل: ollama pull {self.model}")
#                     return False
#             return False
#         except Exception as e:
#             if not self._is_management_command():
#                 print(f"❌ AI وصل نیست! خطا: {e}")
#             return False
    
#     def _call_llm(self, prompt: str) -> str:
#         """ارسال درخواست به مدل و دریافت پاسخ - بدون محدودیت زمانی"""
#         if not self.is_available:
#             return "⚠️ AI در دسترس نیست. لطفاً Ollama را اجرا کنید: ollama serve"
        
#         data = {
#             "model": self.model,
#             "prompt": prompt,
#             "stream": False,  # عدم استفاده از stream برای سادگی
#             "options": {
#                 "temperature": 0.3,
#                 "num_predict": 2048,
#                 "top_k": 40,
#                 "top_p": 0.9
#             }
#         }
        
#         try:
#             # حذف محدودیت زمانی با timeout=None
#             response = requests.post(
#                 f"{self.base_url}/api/generate", 
#                 json=data, 
#                 timeout=None  # این خط مهم است - حذف محدودیت زمانی
#             )
#             if response.status_code == 200:
#                 result = response.json()
#                 return result.get("response", "")
#             return f"خطا: {response.status_code} - {response.text}"
#         except requests.exceptions.Timeout:
#             return "خطا: زمان درخواست به پایان رسید (مدل زمان زیادی نیاز دارد)"
#         except Exception as e:
#             return f"خطا در ارتباط با AI: {str(e)}"
    
#     def summarize_file(self, content: str, filename: str, detail_level: str = "summary") -> dict:
#         prompts = {
#             "summary": f"""فایل "{filename}" را خلاصه کن در ۳-۴ خط:

# {content[:3000]}""",

#             "detailed": f"""فایل "{filename}" را تحلیل کن:

# {content[:4000]}

# موارد زیر را بنویس:
# ۱. موضوع اصلی:
# ۲. اسامی مهم:
# ۳. خلاصه ۵ خطی:""",

#             "full": f"""تحلیل کامل فایل "{filename}":

# {content[:5000]}

# بنویس:
# - موضوع اصلی
# - خلاصه کامل
# - نکات کلیدی
# - نتیجه‌گیری"""
#         }
        
#         response = self._call_llm(prompts.get(detail_level, prompts["summary"]))
#         return {"filename": filename, "summary": response, "detail_level": detail_level}
    
#     def scan_file_for_threats(self, content: str, filename: str, file_size: int) -> dict:
#         prompt = f"""بررسی امنیتی فایل "{filename}" (حجم: {file_size} بایت):

# {content[:3000] if content else "فایل غیر متنی"}

# پاسخ کوتاه:
# ۱. مشکوک است؟ (بله/خیر)
# ۲. نوع خطر:
# ۳. اقدام لازم:"""
        
#         response = self._call_llm(prompt)
        
#         response_lower = response.lower()
#         is_threat = "بله" in response_lower and "خیر" not in response_lower[:20]
        
#         threat_type = "none"
#         if "ویروس" in response_lower:
#             threat_type = "virus"
#         elif "بدافزار" in response_lower:
#             threat_type = "malware"
#         elif "فیشینگ" in response_lower:
#             threat_type = "phishing"
        
#         return {
#             "is_threat": is_threat,
#             "threat_type": threat_type,
#             "description": response[:300],
#             "recommended_action": "block" if is_threat else "allow",
#             "severity": "high" if is_threat else "low"
#         }
    
#     def answer_question_about_file(self, content: str, filename: str, question: str) -> str:
#         prompt = f"""فایل "{filename}":

# {content[:4000]}

# سوال: {question}

# پاسخ:"""
#         return self._call_llm(prompt)
    
#     def analyze_user_behavior(self, user_data: dict, recent_activities: list) -> str:
#         prompt = f"""تحلیل رفتار کاربر:

# نام: {user_data.get('username', 'نامشخص')}
# تعداد فایل‌ها: {user_data.get('total_uploads', 0)}
# نوع فایل‌ها: {json.dumps(user_data.get('file_types', {}), ensure_ascii=False)}
# وضعیت: {'ادمین' if user_data.get('is_staff') else 'کاربر'}

# پاسخ:
# ۱. الگوی رفتاری:
# ۲. نوع فایل‌های غالب:
# ۳. رفتار مشکوک:
# ۴. توصیه به ادمین:"""
        
#         response = self._call_llm(prompt)
        
#         if not response or len(response.strip()) < 30:
#             return f"""📊 تحلیل کاربر {user_data.get('username', 'کاربر')}

# آمار: {user_data.get('total_uploads', 0)} فایل، {len(user_data.get('file_types', {}))} نوع فایل

# داده کافی برای تحلیل دقیق وجود ندارد."""
        
#         return response


# # ایجاد نمونه جهانی
# _is_management = any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'createsuperuser', 'shell', 'test', 'check'])
# if not _is_management:
#     llm_service = LLMService()
# else:
#     llm_service = None





# #(بخش پرامپت تحلیل شخصیت)

# def analyze_user_personality(self, user_data: dict, files_content: str) -> str:
#     """تحلیل شخصیت کاربر بر اساس فایل‌هایش - پرامپت حرفه‌ای"""
    
#     prompt = f"""
# شما یک روانشناس تحلیلگر و کارشناس امنیت سایبری هستید. باید شخصیت کاربر را بر اساس فایل‌های آپلود شده تحلیل کنید.

# **درباره کاربر:**
# - نام کاربری: {user_data.get('username', 'نامشخص')}
# - تعداد کل فایل‌ها: {user_data.get('total_uploads', 0)}
# - تنوع فایل‌ها: {json.dumps(user_data.get('file_types', {}), ensure_ascii=False)}
# - وضعیت: {'ادمین سیستم' if user_data.get('is_staff') else 'کاربر عادی'}

# **محتوای فایل‌های کاربر (نمونه):**
# {files_content[:8000]}

# **تحلیل دقیق مورد نیاز:**

# 1. **شخصیت‌شناسی (Personality Analysis):**
#    - تیپ شخصیتی کاربر چیست؟ (تحلیلی/خلاق/اجرایی/اجتماعی/فنی/هنری/علمی)
#    - ویژگی‌های بارز شخصیتی (مثال: کمال‌گرا، خلاق، محتاط، جسور، منظم، بی‌نظم)
#    - سبک یادگیری (دیداری/شنیداری/خواندنی/عملی)

# 2. **رفتارشناسی (Behavioral Analysis):**
#    - الگوی کاری و مطالعه کاربر چگونه است؟
#    - چه موضوعاتی بیشترین جذابیت را برای او دارند؟
#    - سطح تخصص و دانش فنی کاربر (مبتدی/متوسط/حرفه‌ای/خبره)

# 3. **ارزیابی امنیتی (Security Assessment):**
#    - آیا محتوای مشکوک یا خطرناکی در فایل‌ها وجود دارد؟
#    - آیا فایل‌های رمزگذاری شده یا محافظت شده وجود دارد؟
#    - آیا فایل‌های اجرایی یا اسکریپت‌های خطرناک مشاهده می‌شود؟
#    - آیا فایل‌های مرتبط با هک، کرک یا فعالیت‌های غیرمجاز وجود دارد؟

# 4. **خلاصه اجرایی (Executive Summary):**
#    - کاربر در ۲ خط: (نوع کاربر، سطح ریسک، توصیه اصلی)
#    - توصیه به ادمین برای مدیریت کاربر

# **خروجی را به صورت زیر و با دقت بالا بنویس:**

# 📊 **تحلیل شخصیت کاربر {user_data.get('username')}**

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# **🧠 تیپ شخصیتی:** [نوع تیپ با توضیح مختصر]

# **✨ ویژگی‌های بارز:** 
# • ویژگی 1
# • ویژگی 2
# • ویژگی 3

# **📚 موضوعات مورد علاقه:** 
# • موضوع 1
# • موضوع 2
# • موضوع 3

# **🎯 سطح تخصص:** [مبتدی/متوسط/حرفه‌ای/خبره]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# **⚠️ ارزیابی امنیتی:**

# • **سطح ریسک:** [کم/متوسط/بالا/بحرانی]
# • **نگرانی‌های اصلی:** [لیست نگرانی‌ها]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# **💡 توصیه به ادمین:**

# [توصیه‌های عملی برای مدیریت کاربر]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# """
    
#     return self._call_llm(prompt)


# def analyze_file_content_detailed(self, content: str, filename: str, file_type: str) -> str:
#     """تحلیل عمیق و دقیق محتوای فایل"""
    
#     prompt = f"""
# شما یک تحلیلگر حرفه‌ای اسناد هستید. فایل "{filename}" (نوع: {file_type}) را با دقت کامل تحلیل کنید.

# **محتوای فایل:**
# {content[:10000]}

# **تحلیل دقیق مورد نیاز:**

# 1. **خلاصه اجرایی (۲ خط):**
# 2. **موضوعات اصلی و کلیدی:**
# 3. **افراد، سازمان‌ها و موجودیت‌های مهم:**
# 4. **تاریخ‌ها، اعداد و اطلاعات حساس:**
# 5. **نکات پنهان و زیرلایه‌های محتوا:**
# 6. **ارزیابی اعتبار و کیفیت محتوا:**
# 7. **توصیه‌های عملی بر اساس محتوا:**

# **خروجی را حرفه‌ای و دقیق بنویس:**

# 📄 **تحلیل فایل: {filename}**

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# **📌 خلاصه اجرایی:**
# [۲ خط]

# **🎯 موضوعات اصلی:**
# • موضوع 1
# • موضوع 2
# • موضوع 3

# **👥 موجودیت‌های مهم:**
# • شخص/سازمان 1
# • شخص/سازمان 2

# **⚠️ نکات حساس:**
# • نکته 1
# • نکته 2

# **✅ توصیه:**
# [توصیه عملی]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# """
    
#     return self._call_llm(prompt)



# # 




#llm_service.py
import requests
import json
import sys

class LLMService:
    """سرویس ارتباط با Ollama - با مدل gemma3:27b"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "gemma3:27b"):
        self.base_url = base_url
        self.model = model
        self.is_available = self.check_connection()
    
    def _is_management_command(self) -> bool:
        management_commands = ['makemigrations', 'migrate', 'createsuperuser', 'shell', 'test', 'check']
        return any(cmd in sys.argv for cmd in management_commands)
    
    def check_connection(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                tags = response.json()
                models = [tag.get('name') for tag in tags.get('models', [])]
                if self.model in models:
                    if not self._is_management_command():
                        print(f"✅ AI متصل است - مدل {self.model} آم   اده است")
                    return True
                else:
                    print(f"⚠️ مدل {self.model} یافت نشد. در حال استفاده از مدل پیش‌فرض...")
                    return False
            return False
        except Exception as e:
            print(f"❌ خطا در اتصال: {e}")
            return False
    
    def _call_llm_stream(self, prompt: str) -> str:
        """ارسال درخواست با streaming برای جلوگیری از timeout"""
        if not self.is_available:
            return "⚠️ AI در دسترس نیست. لطفاً Ollama را اجرا کنید."
        
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": True, 
            "options": {
                "temperature": 0.3,
                "num_predict": 1024  # کاهش تعداد توکن‌های خروجی
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=data, 
                stream=True,
                timeout=300  # افزایش timeout به 5 دقیقه
            )
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            full_response += chunk['response']
                        if chunk.get('done', False):
                            break
                    except:
                        continue
            
            return full_response if full_response else "پاسخ دریافت نشد"
            
        except requests.exceptions.Timeout:
            return "خطا: زمان درخواست به پایان رسید. مدل خیلی بزرگ است. لطفاً از مدل کوچکتر استفاده کنید."
        except Exception as e:
            return f"خطا: {str(e)}"
    
    def _call_llm(self, prompt: str) -> str:
        """نسخه ساده بدون streaming"""
        if not self.is_available:
            return "⚠️ AI در دسترس نیست."
        
        # کاهش حجم پرامپت برای سرعت بیشتر
        if len(prompt) > 3000:
            prompt = prompt[:3000] + "..."
        
        data = {

            "model": self.model,
            "prompt": prompt,  
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 500,  # کاهش تعداد توکن‌های خروجی
                "num_ctx": 2048  # کاهش context window
                
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=data, 
                timeout=180  # 3 دقیقه
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            return f"خطا: {response.status_code}"
        except requests.exceptions.Timeout:
            return "خطا: زمان درخواست به پایان رسید. لطفاً از مدل کوچکتر استفاده کنید."
        except Exception as e:
            return f"خطا: {str(e)}"
    
    def analyze_user_personality(self, user_data: dict, files_content: str) -> str:
        """تحلیل شخصیت کاربر - با پرامپت کوتاه‌تر"""
        
        # کاهش حجم محتوا
        if len(files_content) > 3000:
            files_content = files_content[:3000]
        
        prompt = f"""تحلیل شخصیت کاربر:

کاربر: {user_data.get('username')}
تعداد فایل: {user_data.get('total_uploads', 0)}
نوع فایل: {json.dumps(user_data.get('file_types', {}), ensure_ascii=False)}

محتوای فایل‌ها:
{files_content}

بنویس:
1. تیپ شخصیتی:
2. ویژگی‌ها:
3. سطح ریسک: (کم/متوسط/بالا)
4. توصیه به ادمین:"""
        
        return self._call_llm_stream(prompt)  # استفاده از streaming


# ایجاد نمونه جهانی
_is_management = any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'createsuperuser', 'shell', 'test', 'check'])
if not _is_management:
    llm_service = LLMService()
else:
    llm_service = None