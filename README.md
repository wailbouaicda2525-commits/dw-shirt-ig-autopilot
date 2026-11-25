# DW SHIRT — 365-Day Full-Year Instagram Creative Ad Factory (`@dw_shirt`)

مصنع إعلانات إبداعية أوتوماتيكي **كامل لعام واحد (365 يوم — بلا تكرار!)** مخصّص لإنستغرام **`@dw_shirt`** (الطباعة الحرارية حسب الطلب — قسنطينة وتوصيل 58 ولاية).

- **التكلفة:** `$0 / شهر` (Public GitHub Repo = دقائق Actions غير محدودة + استضافة CDN مجانية + Make #2 Scenario #2 بـ `60` كريديت/شهر فقط).
- **المنصّة:** إنستغرام فقط (`@dw_shirt`).
- **الوتيرة:** **1 إشهار/اليوم بالتناوب الأوتوماتيكي لمدة عام كامل (365 يوم)** على الساعة `18:13` بتوقيت الجزائر (`17:13 UTC`):
  - **الأيام الفردية (`R001..R183`):** **183 ريل سينمائي HD** (`1080×1920`, `30fps`, صوت إشهاري مخصّص) عبر **8 محركات إخراج مختلفة**.
  - **الأيام الزوجية (`P001..P182`):** **182 بوستر إبداعي فاخر** (`1080×1350`) عبر **10 تصاميم مختلفة**.
- **تنوع جذري ("فكرة ما تشبه لاختها"):**
  - **365 فكرة إشهارية فريدة 100% بالدارجة الجزائرية** (صفر نسخ مكرّرة!) موزّعة عبر **16 محور إبداعي**:
    1. اللوحة الفارغة والخيال
    2. ضد التقليد والنسخ المكرّرة
    3. المقاهي والمطاعم والكافيتريات (B2B)
    4. الشركات والمحلات والإشهار المتحرك (B2B)
    5. إطلاق براند ملابس جزائري من الصفر
    6. الهدايا الفريدة (نسخة `01/01`)
    7. الثنائيات والأصحاب والإخوة
    8. سويتات الجامعات والدفعات والباك والنوادي
    9. سهولة الطلب في الخاص والماكيت المجانية
    10. جودة الفليكس الحراري HD والقماش الثقيل
    11. ماشي غير تيشيرتات (طوط باق، كاسكيت، طابليات، بولو)
    12. الجيم، الفرق الرياضية، والبطولات
    13. سرعة صيد التراند والعبارات الدارجة
    14. قسنطينة وتوصيل 58 ولاية والدفع عند الاستلام
    15. الفنانين، الرسامين، المصمّمين وصناع المحتوى
    16. البساطة، الفخامة، هوديات الشتاء وأوفرسايز الصيف
  - **23 مشهد استوديو فاخر** (`s01..s23`) بألوان الأسود الفاحم والذهبي المعدني، متطابقة دلالياً مع كل موضوع — **بدون أي كاتالوغ أو موديلات جاهزة**.
  - **10 ستايلات بوسترات:** `bracket_center`, `split_editorial`, `dm_mockup`, `quote_card_gold`, `checklist_minimal`, `side_vertical_bar`, `woven_label`, `b2b_bracket`, `standard`, `apple_manifesto`.
  - **8 محركات ريلز سينمائية:** `cinema_3beat`, `dm_to_reality`, `apple_kinetic`, `bracket_morph`, `split_contrast`, `spotlight_macro`, `flash_manifesto`, `zoom_reveal_quote` (كل محرك بصوت إشهاري خاص!).
  - **ميزة التراند السريع بضغطة زر:** اكتب فكرة تراند اليوم في `Actions → Run workflow` ويطبعلك المصنع بوستر أو ريل وينشرو فوراً على `@dw_shirt`!

---

## التشغيل في 5 دقائق (مرة واحدة برك)

### الخطوة 1: إنشاء ريبو **Public** على GitHub
1. أنشئ ريبو جديد باسم `dw-shirt-ig-autopilot` وخليه **Public** (مهم جداً باش تكون دقائق GitHub Actions لا محدودة وباش إنستغرام يسحب الفيديو والصورة مباشرة بدون أي تكلفة).
2. ارفع كامل محتوى هذا المجلد (تأكّد من رفع `.github/workflows/daily-instagram-ad.yml`).
3. روح إلى `Settings → Actions → General → Workflow permissions` → اختر **Read and write permissions** → **Save**.

### الخطوة 2: بناء السيناريو رقم 2 في حساب **Make #2** (نفس حساب `@TwoPercentQuiz`)
1. أنشئ سيناريو جديد باسم `DW Shirt Instagram Autopilot`.
2. أضف الموديول الأول: **Webhooks → Custom webhook** → سمّه `DW Shirt IG Hook` → انسخ الرابط (مثلاً `https://hook.eu1.make.com/xxxxx`).
3. أضف بعده: **Flow Control → Router** بفرعين:
   - **الفرع 1 (Reels):**
     - الفلتر: `media_type` **Equal to** `reel`
     - الموديول: **Instagram for Business → Create a Reel Post** (حساب `@dw_shirt` المربوط بصفحة فيسبوك)
       - Video URL: `{{1.media_url}}`
       - Caption: `{{1.caption}}`
       - Share to Feed: `Yes`
   - **الفرع 2 (Posters / Photos):**
     - الفلتر: `media_type` **Equal to** `photo`
     - الموديول: **Instagram for Business → Create a Photo Post**
       - Photo URL: `{{1.media_url}}`
       - Caption: `{{1.caption}}`
4. فعّل السيناريو (**ON / Immediately as data arrives**) واضغط **Save**.

> **استهلاك الكريديت في Make #2:** فقط `2` كريديت لكل بوست = `60` كريديت/شهر (ومع `@TwoPercentQuiz` المجموع `~240` من أصل `1,000` مجانية/شهر — و `0 MB` استهلاك داتا لأن إنستغرام يسحب الملف مباشرة من GitHub!).

### الخطوة 3: إضافة 3 Secrets في GitHub
روح لـ `Settings → Secrets and variables → Actions → New repository secret` وأضف:
- `MAKE_DW_WEBHOOK_URL`: رابط الـ Webhook من الخطوة 2
- `TELEGRAM_BOT_TOKEN`: توكن بوت التلغرام تاعك (لتنبيهات النشر المجانية `0` كريديت)
- `TELEGRAM_CHAT_ID`: الـ Chat ID تاعك

### الخطوة 4: أوّل تجربة فورية
روح لـ **Actions → DW SHIRT — Daily Instagram Creative Ad Factory → Run workflow** → اضغط **Run workflow** وخلي المصنع يخدم عام كامل وحده!

---

## التشغيل المحلي / الاختبار (اختياري)
```bash
python dw_factory.py --phase all --mode poster --ad-id P007 --dry-run
python dw_factory.py --phase all --mode reel --ad-id R007 --dry-run
```
