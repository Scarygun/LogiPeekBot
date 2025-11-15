# 📊 Xabar Yuborish Funksiyasi - Batafsil Hisobot

## 📋 Umumiy Ma'lumot

Xabar yuborish funksiyasi (`xabar_yuborish`) - bu botning asosiy funksiyalaridan biri bo'lib, foydalanuvchi tomonidan belgilangan xabarlarni ko'plab Telegram guruhlariga avtomatik ravishda yuborish uchun mo'ljallangan.

---

## 🔄 O'zgarishlar Tarixi

### ✅ Qilingan O'zgarishlar

1. **Akkaunt orqali yuborishga o'tkazildi**
   - **Oldin:** Bot API (aiogram) orqali yuborilardi
   - **Hozir:** Pyrogram (User Account) orqali yuboriladi
   - **Sabab:** Bot API cheklovlari va akkaunt orqali yuborishning qulayligi

2. **Pyrogram Client qo'shildi**
   - `config.py` dan `api_id`, `api_hash` va `phone` o'qiladi
   - Client avtomatik ishga tushiriladi
   - Session fayl avtomatik yaratiladi

3. **Xatoliklar bilan ishlash yaxshilandi**
   - FloodWait xatoliklari to'g'ri boshqariladi
   - ChatWriteForbidden, UserBannedInChannel, ChannelPrivate xatoliklari qayta ishlanadi
   - Batafsil xatolik xabarlari qo'shildi

4. **Muvaffaqiyatli guruhlarni saqlash**
   - `active_groups.json` fayliga muvaffaqiyatli guruhlar saqlanadi
   - Keyingi safar faqat muvaffaqiyatli guruhlarga yuboriladi

---

## 🛠️ Funksiya Tuzilishi

### 📍 Funksiya Parametrlari

```python
async def xabar_yuborish(user_id, xabar, chastota, davomiylik, guruhlar)
```

- **user_id** - Foydalanuvchi ID (yuborishni boshqarish uchun)
- **xabar** - Yuboriladigan xabar matni
- **chastota** - Yuborish chastotasi (Har 30 daqiqa, Har 1 soat, va h.k.)
- **davomiylik** - Yuborish davomiyligi (6 soat, 12 soat, 1 kun, 2 kun)
- **guruhlar** - Guruhlar ro'yxati (list)

---

## ⚙️ Funksiya Ishlash Prinsipi

### 1️⃣ **Boshlang'ich Tekshiruvlar**

```python
# Pyrogram client mavjudligini tekshirish
if user_client is None:
    # Xatolik xabari yuboriladi
    return

# Client ulanib turganligini tekshirish
if not user_client.is_connected:
    await user_client.start()  # Client ishga tushiriladi
```

### 2️⃣ **Chastota va Davomiylik Sozlash**

**Chastota (Interval):**
- `Har 30 daqiqa` → 1800 sekund
- `Har 1 soat` → 3600 sekund
- `Har 3 soat` → 10800 sekund
- `Har 6 soat` → 21600 sekund

**Davomiylik (Duration):**
- `6 soat` → 21600 sekund
- `12 soat` → 43200 sekund
- `1 kun` → 86400 sekund
- `2 kun` → 172800 sekund

### 3️⃣ **Asosiy Yuborish Sikl**

```python
while faol_rassilkalar.get(user_id, False):
    # 1. Davomiylikni tekshirish
    # 2. Har bir guruhga xabar yuborish
    # 3. Xatoliklarni boshqarish
    # 4. Natijalarni saqlash
    # 5. Keyingi yuborishgacha kutish
```

---

## 📤 Xabar Yuborish Jarayoni

### **Qadam 1: Guruh ID ni Tozalash**

```python
# URL formatidan username olish
if group_id.startswith("https://t.me/"):
    group_username = group_id.split("/")[-1]
    target = group_username
```

### **Qadam 2: Xabar Yuborish**

```python
await user_client.send_message(target, xabar)
```

### **Qadam 3: Xatoliklarni Boshqarish**

#### **FloodWait (Tez yuborish cheklovi)**
```python
except FloodWait as e:
    retry_after = e.value  # Telegram so'ragan kutish vaqti
    await asyncio.sleep(retry_after)
    # Qayta urinib ko'rish
```

#### **ChatWriteForbidden (Yozish huquqi yo'q)**
```python
except ChatWriteForbidden:
    # Akkaunt guruhga yozish huquqiga ega emas
    xatoliklar += 1
```

#### **UserBannedInChannel (Bloklangan)**
```python
except UserBannedInChannel:
    # Akkaunt guruhda bloklangan
    xatoliklar += 1
```

#### **ChannelPrivate (Yopiq guruh)**
```python
except ChannelPrivate:
    # Guruh yopiq yoki topilmadi
    xatoliklar += 1
```

---

## 📊 Natijalarni Saqlash

### **Muvaffaqiyatli Guruhlar**

Har bir muvaffaqiyatli yuborilgan guruh `active_groups.json` fayliga saqlanadi:

```json
[
  "https://t.me/logipeek19999",
  "https://t.me/logistica_uzb",
  ...
]
```

**Afzalliklari:**
- Keyingi safar faqat muvaffaqiyatli guruhlarga yuboriladi
- Vaqt tejash
- Xatoliklarni kamaytirish

---

## 🔒 Xavfsizlik va Cheklovlar

### **Flood Control**

- Har bir xabar orasida **0.5 soniya** kutish
- Telegram FloodWait xatoligida avtomatik kutish
- Retry mexanizmi

### **Davomiylik Cheklovi**

- Belgilangan vaqtdan keyin avtomatik to'xtaydi
- Foydalanuvchiga xabar yuboriladi

### **To'xtatish Imkoniyati**

- Foydalanuvchi istalgan vaqtda to'xtatishi mumkin
- `faol_rassilkalar[user_id] = False` orqali

---

## 📈 Statistika va Monitoring

### **Konsolga Chiqadigan Ma'lumotlar**

```
✅ Xabar yuborish boshlandi (akkaunt orqali): 108 ta guruhga har 3600 sekundda
✅ Yuborildi (akkaunt orqali): logipeek19999
❌ logistica_uzb: Akkaunt guruhga yozish huquqiga ega emas
⏳ Flood control: groupname uchun 30 soniya kutish kerak

📊 === Yuborish natijasi (akkaunt orqali) ===
✅ Muvaffaqiyatli: 95 ta
❌ Xatoliklar: 13 ta
📈 Jami: 108 ta guruh

💾 95 ta muvaffaqiyatli guruh 'active_groups.json' fayliga saqlandi
```

---

## 🎯 Foydalanish Misoli

### **1. Xabar Sozlash**

```
Foydalanuvchi: ⚙️ Xabar sozlamalari
Bot: Yuboriladigan xabarni kiriting
Foydalanuvchi: Salom! Bu test xabari
Bot: Chastotani tanlang
Foydalanuvchi: Har 1 soat
Bot: Davomiylikni tanlang
Foydalanuvchi: 1 kun
```

### **2. Yuborishni Boshlash**

```
Foydalanuvchi: ▶️ Yuborishni boshlash
Bot: 🚀 Xabar yuborish boshlandi (akkaunt orqali)!
```

### **3. Yuborish Jarayoni**

- Har 1 soatda barcha guruhlarga xabar yuboriladi
- 1 kun davomida davom etadi
- Muvaffaqiyatli guruhlar saqlanadi

---

## ⚠️ Muhim Eslatmalar

### **Talablar**

1. ✅ **Akkaunt guruhlarga a'zo bo'lishi kerak**
   - Akkaunt a'zo bo'lmasa xabar yuborilmaydi
   - Har bir guruhga alohida qo'shish kerak

2. ✅ **Config.py to'g'ri sozlangan bo'lishi kerak**
   - `api_id` - integer raqam
   - `api_hash` - 32 ta hexadecimal belgi
   - `phone` - telefon raqami (+998...)

3. ✅ **Pyrogram Client ishga tushgan bo'lishi kerak**
   - Birinchi marta telefon kodi so'raladi
   - Session fayl yaratiladi

### **Cheklovlar**

- ❌ Spam va reklama taqiqlangan
- ❌ Juda tez yuborish FloodWait xatoligiga olib keladi
- ❌ Bloklangan guruhlarga yuborish mumkin emas

---

## 🔧 Texnik Detallar

### **Ishlatilgan Kutubxonalar**

- **Pyrogram** - Telegram Client API
- **aiogram** - Bot API (foydalanuvchi bilan aloqa uchun)
- **asyncio** - Asinxron operatsiyalar

### **Fayllar**

- `groups.json` - Barcha guruhlar ro'yxati
- `active_groups.json` - Muvaffaqiyatli guruhlar ro'yxati
- `config.py` - API ma'lumotlari
- `user_account.session` - Pyrogram session fayli

---

## 📝 Kod Misoli

```python
# Funksiyani chaqirish
asyncio.create_task(
    xabar_yuborish(
        user_id=8093402925,
        xabar="Salom! Bu test xabari",
        chastota="Har 1 soat",
        davomiylik="1 kun",
        guruhlar=["https://t.me/logipeek19999", ...]
    )
)
```

---

## 🎉 Xulosa

Xabar yuborish funksiyasi endi **akkaunt orqali** ishlaydi va quyidagi afzalliklarga ega:

✅ **Qulaylik** - Akkaunt orqali yuborish
✅ **Xavfsizlik** - Flood control va xatoliklar bilan ishlash
✅ **Samaradorlik** - Muvaffaqiyatli guruhlarni saqlash
✅ **Monitoring** - Batafsil statistika va xabarlar
✅ **To'xtatish** - Istalgan vaqtda to'xtatish imkoniyati

---

**Yaratilgan sana:** 2025-yil  
**Oxirgi yangilanish:** Akkaunt orqali yuborishga o'tkazildi  
**Versiya:** 2.0

