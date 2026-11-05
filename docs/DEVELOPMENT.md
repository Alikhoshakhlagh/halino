# حالینو — راهنمای توسعه

> مرجع فنی پروژه: استک، ساختار، رفتار صفحه‌ها، موتور پیشنهاد و دام‌هایی که سر راه بوده‌اند.
> آخرین به‌روزرسانی: آبان ۱۴۰۵.

## ۱. پروژه در یک پاراگراف

**حالینو** وب‌اپ فارسی و راست‌به‌چپ پیشنهاد محتوا/فعالیت بر اساس حال روزانه‌ی کاربر
است (فیلم، سریال، کتاب، پادکست، مقاله، کافه، ورزش، مدیتیشن، نوشتن، بازی). پروژه‌ی
دانشگاهیِ فردی. موتور پیشنهاد Rule-Based روی «بردار تگ» + یک Naive Bayes بسیار ساده
برای بازچینش. ورود با شماره موبایل + کد یک‌بارمصرف.

## ۲. استک — دقیقاً چه چیزی استفاده شده

| لایه | فناوری | نکته |
|---|---|---|
| بک‌اند | **Python + Django 5.2 + DRF** | فقط API؛ ورود با JWT (`simplejwt`) و CORS با `django-cors-headers` |
| دیتابیس | **SQLite** (توسعه) | برای PostgreSQL فقط بلوک `DATABASES` در `config/settings.py` عوض می‌شود |
| فرانت | **HTML + SCSS + JavaScript ساده** | بدون فریم‌ورک؛ فقط `sass` برای ساخت CSS لازم است |
| آیکون | SVG در `js/components/icon.js` (سبک Lucide) | بدون فونت آیکون، بدون CDN |
| چهره‌های مود | SVG در `js/components/face.js` | بدون ایموجی |
| فونت | Vazirmatn لوکال در `frontend/assets/fonts` | بدون درخواست بیرونی |

## ۳. اجرا

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_base        # شهر، تگ، دسته، مود، سؤال، ۱۰ مناسبت ایرانی + ۳۶۷ روز جهانی، آیتم‌های غیرفیلم
python manage.py import_titles    # ۲۵۰ فیلم/سریال از content/fixtures/top_titles.json
python manage.py createsuperuser  # پنل ادمین
python manage.py runserver
python manage.py test
```

فرانت: داخل `frontend` بزن `python serve.py`. برای تغییر استایل:
`sass --watch scss/main.scss css/main.css --no-source-map`.

- ورود: شماره موبایل → کد OTP در **کنسول چاپ می‌شود و روی صفحه‌ی تأیید هم نمایش داده می‌شود** (`HALINO_OTP_CONSOLE = True`). سرویس پیامک وصل نیست.
- کاربر نمونه با داده‌ی فیک: `python manage.py demo_user` (همان کاربر را هر بار از نو می‌سازد).
- کاربر دمو: `09121234567`.
- `manage.py` خروجی کنسول را UTF-8 می‌کند (کنسول ویندوز cp1256 است و روی فارسی کرش می‌کرد).

## ۴. ساختار

```
backend/
  config/    settings, urls
  accounts/  User سفارشی (phone = username)، City (is_supported)، OTPCode، forms.py (اعتبارسنجی شماره و کد)
  content/   Tag, Category(is_serial, needs_city), Item, ItemTag, Occasion, taxonomy.py
             management/commands/import_titles.py
  journey/   Mood(face, energy, valence), MoodEntry, Question/Option/Answer,
             UserTagAffinity, UserItemStatus, DailyRecommendation,
             engine.py (موتور), ml.py (Naive Bayes), jalali.py (تقویم شمسی بدون پکیج),
             tests.py, management/commands/{seed_base, demo_moods}
  api/       urls.py, serializers.py, answers.py, tests.py,
             views/{auth, today, questions, calendar, catalog, profile}.py
frontend/
  index, login, verify, onboarding, daily-questions, calendar, categories,
  category-detail, item-detail, profile (.html)
  scss/      main, _root, _mixins, base/, layout/, components/, pages/, animations/
  js/        config, utils, api, layout, animations, auth/, components/, pages/
docs/        ERD.md, ml.md, DEVELOPMENT.md (این فایل)
```

## ۵. صفحه‌ها و رفتار فعلی

- **ورود / تأیید کد** (`login`, `verify`) — بدون صفحه‌ی ثبت‌نام؛ کاربر جدید بعد از کد به آنبوردینگ می‌رود.
- **آنبوردینگ** (`onboarding`) — اجباری؛ مرحله‌ی اول اسم و شهر و بعد هر سؤال یک مرحله. تا تمام نشود وارد برنامه نمی‌شود.
- **امروز** (`index`):
  - **بدون مود:** کارت «امروز چه حالی داری؟» با هر ۹ مود در شبکه‌ی ۳×۳ و دکمه‌ی تأیید.
  - **با مود:** چهره‌ی مود بالای صفحه است و زدنش شیت تغییر مود را باز می‌کند؛ اگر سؤال‌های روز جواب داده نشده باشند یک لینک به آن‌ها دیده می‌شود.
  - **پیشنهادها:** «در حال انجام»، «متناسب با حالت» (فقط با مود) و «پیشنهاد روز». هر ردیف تیک انجام و ضربدر «نمی‌خوام» دارد؛ انجام‌شده علامت می‌خورد و ردشده حذف می‌شود.
- **سؤال‌های روز** (`daily-questions`) — اختیاری؛ بعد از ثبت مود باز می‌شود، دو جعبه دارد و «بعداً جواب می‌دم» به امروز برمی‌گردد.
- **تقویم** (`calendar`) — گرید ماه شمسی با چهره (زدن روی روزهای گذشته و امروز حال آن روز را ثبت یا عوض می‌کند؛ برای گذشته سؤال اضافه و پیشنهاد جدید ساخته نمی‌شود)، گزارش ماهانه، نمودار نوسان و سه آمار.
- **دسته‌ها** (`categories`, `category-detail`) — تایل‌ها و فهرست آیتم‌های هر دسته با وضعیت.
- **آیتم** (`item-detail`) — بنر، تگ‌ها، توضیح، امتیاز، انجام دادم / شروع کردم (دنباله‌دارها) / دیگه پیشنهاد نده.
- **پروفایل** (`profile`) — «بهتر بشناسیمت» (سؤال‌های scope=profile)، ویرایش اسم و شهر، موارد ردشده با «برگردون» و خروج.

## ۶. موتور پیشنهاد (`journey/engine.py`) — قوانین را عوض نکن

- همه‌چیز «بردار تگ» است: پروفایل کاربر (`UserTagAffinity` از آنبوردینگ + بازخورد)،
  مود (`MoodTag`)، آیتم (`ItemTag`). امتیاز = ضرب داخلی + نویز کوچک با seed ثابت.
- **`build_day_layer`** («پیشنهاد روز») بر دو پایه: شناخت کلی از کاربر + مناسبت روز.
  ۱) آیتم‌های قفل‌شده‌ی دستور مدیر روی مناسبت ۲) یک آیتم تضمینی «به مناسبتِ» مناسبت
  اصلی روز (`_occasion_pick`: باید تگ مناسبت را داشته باشد، بین آن‌ها سلیقه‌ی کاربر
  انتخاب می‌کند) و تگ‌های مناسبت روی بقیه هم وزن می‌گیرند ۳) یک اسلات کافه/دورهمی
  **فقط** اگر شهر پشتیبانی‌شده و وزن تگ‌های `social/outdoor` مثبت باشد ۴) بقیه با موتور.
  مناسبت هر روز از `content/national_days.py` (یک روز جهانی برای هر روز سال، انتخاب‌شده
  برای محتوای حالینو) یا تقویم ایرانی می‌آید؛ ادمین با اولویت بالاتر override می‌کند.
  روزی یک بار ساخته و در `DailyRecommendation(source="profile", occasion=…)` ذخیره می‌شود.
- **`build_mood_layer`** («متناسب با حالت»): پروفایل×۰٫۵ + مود×۱ + پاسخ‌های روز×۰٫۷۵؛
  با هر تغییر مود بازسازی می‌شود. اینجا تنها جایی است که ML وارد می‌شود.
- سه قانون بیرون فرمول: گیت شهری (`Category.needs_city`)، دنباله‌دار (`Category.is_serial`:
  تا کتاب/سریال فعلی تمام نشده جدید نده)، ضدتکرار ۳۰ روز (با استخر خالی مرحله‌به‌مرحله شل می‌شود).
- **مناسبت** (`content.Occasion`): `calendar` شمسی/میلادی، `source` = iran / national /
  admin، `priority`، `tags`، `pinned_items`، `year` اختیاری برای دستور یک‌باره.
- **بازخورد:** `apply_feedback()` وضعیت را می‌نویسد و پروفایل تگ را بازمی‌سازد.
  «نمی‌خوام» دائمی است؛ «انجام دادم» یادآوری ریویو ۹۰ روز بعد می‌گذارد.

## ۷. ML (`journey/ml.py`, `docs/ml.md`)

Multinomial Naive Bayes به‌ازای هر کاربر، پایتون خالص. توکن‌ها = تگ‌های آیتم (شمارش =
وزن) + `mood:<id>` روز بازخورد. خروجی `P(like | tags, mood)`. فقط در `build_mood_layer`
از طریق `_select(..., rerank=ml.reranker(user, mood))`: امتیاز قاعده‌محور × احتمال.
زیر **۱۰** رکورد بازخورد غیرفعال. تست: `MLTests` در `journey/tests.py`.

## ۸. سیستم طراحی (`frontend/scss`)

- **فقط تم روشن، مینیمال و پاستیلی.** همه‌ی رنگ‌ها فقط در `_root.scss` هستند؛ زرد برای پس‌زمینه استفاده نمی‌شود.
- **رنگ مود و دسته از نوعشان می‌آید:** `data-mood` و `data-category` → `base/_data-colors.scss` متغیر `--c` را از `:root` می‌گذارد. فیلد `color` دیتابیس روی UI اثری ندارد. دسته‌ی جدید رنگ پیش‌فرض می‌گیرد مگر اینکه به `$categories` و `:root` اضافه شود.
- آیکون دسته از **slug** می‌آید: `createIcon(category.slug)`. برای slug ناشناخته آیکون tag کشیده می‌شود؛ آیکون جدید را به `js/components/icon.js` اضافه کن.
- توکن‌ها: فاصله (`--space-*`)، تایپ (`--text-*`، متن اصلی ۱۵px)، شعاع (`--radius-*`)، حرکت (`--duration-*`).
- استایل‌های مشترک در `_mixins.scss`: `flex`، `stack`، `grid`، `card`، `square`، `pressable`، `selectable`، `enter-list`.
- فقط logical properties؛ کنتراست متن‌ها حداقل ۴.۵:۱.
- انیمیشن تا جای ممکن با CSS است و همه پشت `prefers-reduced-motion` هستند.

## ۹. حریم داده — قانون UI

هیچ‌جای UI نباید نشان دهد: پاسخ‌های پرسشنامه، تگ‌ها/وزن‌های کاربر، energy/valence،
امتیاز موتور، شهر (جز داخل فرم تنظیمات). پروفایل فقط نام + شماره + تنظیمات.

## ۱۰. دام‌هایی که دو بار گزیدند

- کلاسی که `display` ست می‌کند بر `[hidden]` مرورگر غلبه می‌کند → ریست دارد `[hidden]{display:none!important}`.
- `annotate()` ترتیب `Meta.ordering` را می‌اندازد → بعدش `order_by` صریح.
- مدل `User` سفارشی است؛ هیچ‌وقت با `User` پیش‌فرض migrate نکن.

## ۱۱. کارهای باز

- سرویس پیامک واقعی برای OTP + هش کردن کد.
- مستندات دانشگاهی (گزارش، ارائه) — هنوز نوشته نشده.
- تقویم روزهای جهانی (`content/national_days.py`) برای هر روز یک مناسبت دارد که دستی انتخاب شده؛ نقل‌قول بیشترشان خالی است و از ادمین قابل ویرایش/افزایش.
- انتقال به PostgreSQL برای تحویل نهایی.
