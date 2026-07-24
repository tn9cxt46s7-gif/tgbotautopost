/* INPUT CARS — Krāsošana / Paint shop */

const CAR_DATA = {
    'Audi': ['A1', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'Q2', 'Q3', 'Q5', 'Q7', 'Q8', 'TT', 'R8', 'e-tron', 'Cits'],
    'BMW': ['1', '2', '3', '4', '5', '7', 'X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'i3', 'i4', 'iX', 'Cits'],
    'Mercedes-Benz': ['A', 'B', 'C', 'E', 'S', 'CLA', 'CLS', 'GLA', 'GLB', 'GLC', 'GLE', 'GLS', 'G', 'EQC', 'Cits'],
    'Volkswagen': ['Polo', 'Golf', 'Passat', 'Arteon', 'Tiguan', 'T-Roc', 'Touareg', 'ID.3', 'ID.4', 'Cits'],
    'Toyota': ['Yaris', 'Corolla', 'Camry', 'RAV4', 'C-HR', 'Land Cruiser', 'Prius', 'Cits'],
    'Ford': ['Fiesta', 'Focus', 'Mondeo', 'Mustang', 'Kuga', 'Puma', 'Explorer', 'Cits'],
    'Opel': ['Corsa', 'Astra', 'Insignia', 'Mokka', 'Crossland', 'Grandland', 'Cits'],
    'Volvo': ['S60', 'S90', 'V60', 'V90', 'XC40', 'XC60', 'XC90', 'C40', 'Cits'],
    'Skoda': ['Fabia', 'Scala', 'Octavia', 'Superb', 'Kamiq', 'Karoq', 'Kodiaq', 'Enyaq', 'Cits'],
    'Hyundai': ['i10', 'i20', 'i30', 'Tucson', 'Santa Fe', 'Kona', 'Ioniq', 'Cits'],
    'Kia': ['Picanto', 'Rio', 'Ceed', 'Sportage', 'Sorento', 'Niro', 'EV6', 'Cits'],
    'Nissan': ['Micra', 'Juke', 'Qashqai', 'X-Trail', 'Leaf', 'Cits'],
    'Honda': ['Jazz', 'Civic', 'Accord', 'CR-V', 'HR-V', 'Cits'],
    'Mazda': ['2', '3', '6', 'CX-3', 'CX-30', 'CX-5', 'MX-5', 'Cits'],
    'Peugeot': ['208', '308', '508', '2008', '3008', '5008', 'Cits'],
    'Renault': ['Clio', 'Megane', 'Captur', 'Kadjar', 'Arkana', 'Cits'],
    'Citroën': ['C3', 'C4', 'C5', 'Berlingo', 'Cits'],
    'Fiat': ['500', 'Panda', 'Tipo', 'Doblo', 'Cits'],
    'Seat': ['Ibiza', 'Leon', 'Arona', 'Ateca', 'Tarraco', 'Cits'],
    'Porsche': ['911', 'Cayenne', 'Macan', 'Panamera', 'Taycan', 'Cits'],
    'Land Rover': ['Defender', 'Discovery', 'Range Rover', 'Evoque', 'Cits'],
    'Jeep': ['Renegade', 'Compass', 'Cherokee', 'Wrangler', 'Cits'],
    'Tesla': ['Model 3', 'Model Y', 'Model S', 'Model X', 'Cits'],
    'Lexus': ['IS', 'ES', 'NX', 'RX', 'UX', 'Cits'],
    'Subaru': ['Impreza', 'Forester', 'Outback', 'XV', 'Cits'],
    'Mitsubishi': ['Space Star', 'ASX', 'Outlander', 'L200', 'Cits'],
    'Cits': ['Cits modelis']
};

const SERVICE_KEYS = ['svcFull', 'svcPartial', 'svcBody', 'svcTouch', 'svcAnticor', 'svcInterior', 'svcInteriorPromo', 'svcOther'];

const I18N = {
    lv: {
        pageTitle: 'Input Cars | Krāsošanas darbi',
        heroTagline: 'PROFESIONĀLA AUTO KRĀSOŠANA',
        heroBtn: 'PIETEIKTIES',
        hoursTitle: '🕒 DARBA LAIKS',
        hoursWeek: 'P-Pk: 09:00 - 17:00',
        hoursWeekend: 'S-Sv: Slēgts',
        whyTitle: 'KĀPĒC IZVĒLĒTIES MŪS',
        why1Title: 'PERFEKTA KRĀSOJUMA KVALITĀTE',
        why1Text: 'Krāsojam ar profesionāliem materiāliem. Katrs auto saņem individuālu pieeju.',
        why2Title: 'MALĒJU PIEREDZE',
        why2Text: 'Mūsu meistari specializējas virsbūves krāsošanā un remontā.',
        why3Title: 'GARANTIJA UZ DARBU',
        why3Text: 'Mēs garantējam krāsojuma kvalitāti un ilgmūžību.',
        why4Title: 'KRĀSOŠANAS KAMERA',
        why4Text: 'Mūsdienīga aprīkojuma krāsošanas kamera un precīza krāsu atlase.',
        portfolioTitle: 'MŪSU DARBI — PIEMĒRI',
        portLabel1: 'PILNA KRĀSOŠANA',
        portLabel2: 'DAĻĒJA KRĀSOŠANA',
        portLabel3: 'PIEMĒRS — PIRMS/PĒC',
        findTitle: 'ATRAST MŪS',
        address: ' ',
        footerCopy: '© INPUT CARS | AUTO KRĀSOŠANA',
        aiHeader: 'INPUT CARS ASISTENTS',
        aiWelcome: 'Sveiki! Jautājiet par krāsošanas pakalpojumiem.',
        aiPlaceholder: 'Rakstiet šeit...',
        formTitle: 'PIETEIKTIES KRĀSOŠANAI',
        namePh: 'Vārds un Uzvārds *',
        phonePh: 'Tālrunis *',
        emailPh: 'E-pasts *',
        servicePh: 'Izvēlieties pakalpojumu *',
        brandPh: 'Auto marka *',
        modelPh: 'Auto modelis *',
        descPh: 'Aprakstiet bojājumu — ko vēlaties nokrāsot? *',
        photoLabel: 'Pievienot foto (bojājuma zona)',
        gdpr: 'Es piekrītu personas datu apstrādei saskaņā ar GDPR.',
        submitBtn: 'Nosūtīt pieteikumu',
        backBtn: '← Atpakaļ',
        successTitle: 'PIETEIKUMS PIEŅEMTS!',
        successText: 'Jūs esat pieteicies. Gaidiet — mēs sazināsimies ar Jums tuvākajā laikā.',
        successCloseBtn: 'Aizvērt',
        recaptchaError: 'Lūdzu, apstipriniet reCAPTCHA',
        sendError: 'Kļūda nosūtot. Mēģiniet vēlreiz.',
        sending: 'Nosūta...',
        fileTooBig: 'Fails pārāk liels (maks. 5 MB)',
        aiReply: 'Paldies! Lai pieteiktos krāsošanai, nospiediet PIETEIKTIES.',
        svcFull: 'Pilna auto krāsošana',
        svcPartial: 'Daļēja krāsošana',
        svcBody: 'Virsbūves remonts',
        svcTouch: 'Rāmis / krāsas korekcija',
        svcAnticor: 'Antikorozijas apstrāde',
        svcInterior: 'Salona tīrīšana',
        svcInteriorPromo: '🔥 Pilna salona ķīmiskā tīrīšana — AKCIJA -50% (tikai 12.07)',
        svcOther: 'Cits pakalpojums',
        cleaningTitle: 'SALONA TĪRĪŠANA UN ĶĪMISKĀ TĪRĪŠANA',
        cleaningText: 'Rūpīga salona tīrīšana un dziļā ķīmiskā tīrīšana — atgriezīsim Jūsu auto salonam svaigumu un tīrību.',
        promoBadge: 'AKCIJA',
        promoDate: 'TIKAI 12.07.2026',
        promoTitle: 'PILNA SALONA ĶĪMISKĀ TĪRĪŠANA',
        promoDesc: 'Viena diena, lieliska cena! Pilna auto salona ķīmiskā tīrīšana ar -50% atlaidi.',
        promoOldPrice: '60 €',
        promoNewPrice: '30 €',
        promoDiscount: '-50%',
        promoBtn: 'PIETEIKTIES AKCIJAI',
        themeDark: 'Tumšā',
        themeLight: 'Gaišā',
        themePaint: 'Krāsas',
        langPanelTitle: 'Valoda',
        themePanelTitle: 'Tēma'
    },
    ru: {
        pageTitle: 'Input Cars | Малярные работы',
        heroTagline: 'ПРОФЕССИОНАЛЬНАЯ ПОКРАСКА АВТО',
        heroBtn: 'ЗАПИСАТЬСЯ',
        hoursTitle: '🕒 РЕЖИМ РАБОТЫ',
        hoursWeek: 'Пн-Пт: 09:00 - 17:00',
        hoursWeekend: 'Сб-Вс: Закрыто',
        whyTitle: 'ПОЧЕМУ ВЫБИРАЮТ НАС',
        why1Title: 'КАЧЕСТВЕННАЯ ПОКРАСКА',
        why1Text: 'Работаем профессиональными материалами. Индивидуальный подход к каждому авто.',
        why2Title: 'ОПЫТ МАЛЯРОВ',
        why2Text: 'Мастера специализируются на покраске и кузовном ремонте.',
        why3Title: 'ГАРАНТИЯ НА РАБОТУ',
        why3Text: 'Гарантируем качество и долговечность покрытия.',
        why4Title: 'ПОКРАСОЧНАЯ КАМЕРА',
        why4Text: 'Современная камера и точный подбор цвета краски.',
        portfolioTitle: 'НАШИ РАБОТЫ — ПРИМЕРЫ',
        portLabel1: 'ПОЛНАЯ ПОКРАСКА',
        portLabel2: 'ЛОКАЛЬНАЯ ПОКРАСКА',
        portLabel3: 'ПРИМЕР — ДО/ПОСЛЕ',
        findTitle: 'КАК НАС НАЙТИ',
        address: ' ',
        footerCopy: '© INPUT CARS | ПОКРАСОЧНЫЕ РАБОТЫ',
        aiHeader: 'АССИСТЕНТ INPUT CARS',
        aiWelcome: 'Здравствуйте! Спросите о покраске авто.',
        aiPlaceholder: 'Напишите здесь...',
        formTitle: 'ЗАПИСЬ НА ПОКРАСКУ',
        namePh: 'Имя и Фамилия *',
        phonePh: 'Телефон *',
        emailPh: 'E-mail *',
        servicePh: 'Выберите услугу *',
        brandPh: 'Марка авто *',
        modelPh: 'Модель авто *',
        descPh: 'Опишите повреждение — что нужно покрасить? *',
        photoLabel: 'Добавить фото (зона повреждения)',
        gdpr: 'Я согласен на обработку персональных данных согласно GDPR.',
        submitBtn: 'Отправить заявку',
        backBtn: '← Назад',
        successTitle: 'ВЫ ЗАПИСАНЫ!',
        successText: 'Ждите ответа — мы свяжемся с вами в ближайшее время.',
        successCloseBtn: 'Закрыть',
        recaptchaError: 'Пройдите проверку reCAPTCHA',
        sendError: 'Ошибка отправки. Попробуйте снова.',
        sending: 'Отправка...',
        fileTooBig: 'Файл слишком большой (макс. 5 МБ)',
        aiReply: 'Спасибо! Для записи на покраску нажмите ЗАПИСАТЬСЯ.',
        svcFull: 'Полная покраска авто',
        svcPartial: 'Локальная покраска',
        svcBody: 'Кузовной ремонт',
        svcTouch: 'Подкраска / коррекция',
        svcAnticor: 'Антикоррозийная обработка',
        svcInterior: 'Чистка салона',
        svcInteriorPromo: '🔥 Полная химчистка салона — АКЦИЯ -50% (только 12.07)',
        svcOther: 'Другое',
        cleaningTitle: 'ЧИСТКА И ХИМЧИСТКА САЛОНА',
        cleaningText: 'Тщательная чистка салона и глубокая химчистка — вернём вашему салону свежесть и чистоту.',
        promoBadge: 'АКЦИЯ',
        promoDate: 'ТОЛЬКО 12.07.2026',
        promoTitle: 'ПОЛНАЯ ХИМЧИСТКА САЛОНА',
        promoDesc: 'Один день, отличная цена! Полная химчистка салона авто со скидкой -50%.',
        promoOldPrice: '60 €',
        promoNewPrice: '30 €',
        promoDiscount: '-50%',
        promoBtn: 'ЗАПИСАТЬСЯ НА АКЦИЮ',
        themeDark: 'Тёмная',
        themeLight: 'Светлая',
        themePaint: 'Краска',
        langPanelTitle: 'Язык',
        themePanelTitle: 'Тема'
    },
    et: {
        pageTitle: 'Input Cars | Värvitööd',
        heroTagline: 'PROFESSIONAALNE AUTO VÄRVIMINE',
        heroBtn: 'BRONEERI',
        hoursTitle: '🕒 TÖÖAEG',
        hoursWeek: 'E-R: 09:00 - 17:00',
        hoursWeekend: 'L-P: Suletud',
        whyTitle: 'MIKS VALIDA MEID',
        why1Title: 'PERFEKTNE VÄRVIKVALITEET',
        why1Text: 'Värvime professionaalsete materjalidega. Iga auto saab individuaalse lähenemise.',
        why2Title: 'VÄRVIMEISTrite KOGEMUS',
        why2Text: 'Meistrid on spetsialiseerunud kere värvimisele ja remondile.',
        why3Title: 'GARANTII TÖÖLE',
        why3Text: 'Garanteerime värvikihi kvaliteedi ja vastupidavuse.',
        why4Title: 'VÄRVIKAMBER',
        why4Text: 'Kaasaegne värvikamber ja täpne värvi valik.',
        portfolioTitle: 'MEIE TÖÖD — NÄITED',
        portLabel1: 'TÄIELIK VÄRVIMINE',
        portLabel2: 'OSALINE VÄRVIMINE',
        portLabel3: 'NÄIDE — ENNE/PÄRAST',
        findTitle: 'LEIA MEID',
        address: ' ',
        footerCopy: '© INPUT CARS | AUTO VÄRVIMINE',
        aiHeader: 'INPUT CARS ASSISTENT',
        aiWelcome: 'Tere! Küsige värvimisteenuste kohta.',
        aiPlaceholder: 'Kirjutage siia...',
        formTitle: 'BRONEERI VÄRVIMINE',
        namePh: 'Nimi *',
        phonePh: 'Telefon *',
        emailPh: 'E-post *',
        servicePh: 'Valige teenus *',
        brandPh: 'Auto mark *',
        modelPh: 'Auto mudel *',
        descPh: 'Kirjeldage kahjustust — mida soovite värvida? *',
        photoLabel: 'Lisa foto (kahjustuse tsoon)',
        gdpr: 'Nõustun isikuandmete töötlemisega GDPR kohaselt.',
        submitBtn: 'Saada taotlus',
        backBtn: '← Tagasi',
        successTitle: 'BRONEERING VASTU VÕETUD!',
        successText: 'Oodake — võtame Teiega peagi ühendust.',
        successCloseBtn: 'Sulge',
        recaptchaError: 'Palun kinnitage reCAPTCHA',
        sendError: 'Saatmise viga. Proovige uuesti.',
        sending: 'Saadan...',
        fileTooBig: 'Fail liiga suur (max 5 MB)',
        aiReply: 'Aitäh! Broneerimiseks vajutage BRONEERI.',
        svcFull: 'Täielik auto värvimine',
        svcPartial: 'Osaline värvimine',
        svcBody: 'Kere remont',
        svcTouch: 'Kriimude parandamine',
        svcAnticor: 'Korrosioonikaitse',
        svcInterior: 'Salongi puhastus',
        svcInteriorPromo: '🔥 Täielik salongi keemiline puhastus — SOODUSPAKKUMINE -50% (ainult 12.07)',
        svcOther: 'Muu teenus',
        cleaningTitle: 'SALONGI PUHASTUS JA KEEMILINE PUHASTUS',
        cleaningText: 'Põhjalik salongi puhastus ja sügavpuhastus — toome Teie auto salongi tagasi värskuse ja puhtuse.',
        promoBadge: 'SOODUSPAKKUMINE',
        promoDate: 'AINULT 12.07.2026',
        promoTitle: 'TÄIELIK SALONGI KEEMILINE PUHASTUS',
        promoDesc: 'Üks päev, suurepärane hind! Täielik auto salongi keemiline puhastus -50% allahindlusega.',
        promoOldPrice: '60 €',
        promoNewPrice: '30 €',
        promoDiscount: '-50%',
        promoBtn: 'BRONEERI SOODUSPAKKUMINE',
        themeDark: 'Tume',
        themeLight: 'Hele',
        themePaint: 'Värv',
        langPanelTitle: 'Keel',
        themePanelTitle: 'Teema'
    },
    en: {
        pageTitle: 'Input Cars | Auto Paint Shop',
        heroTagline: 'PROFESSIONAL AUTO PAINTING',
        heroBtn: 'BOOK NOW',
        hoursTitle: '🕒 OPENING HOURS',
        hoursWeek: 'Mon-Fri: 09:00 - 17:00',
        hoursWeekend: 'Sat-Sun: Closed',
        whyTitle: 'WHY CHOOSE US',
        why1Title: 'PERFECT PAINT FINISH',
        why1Text: 'We use professional materials. Every car gets individual attention.',
        why2Title: 'PAINTER EXPERIENCE',
        why2Text: 'Our masters specialize in body painting and repair.',
        why3Title: 'WORK WARRANTY',
        why3Text: 'We guarantee paint quality and durability.',
        why4Title: 'PAINT BOOTH',
        why4Text: 'Modern paint booth and precise color matching.',
        portfolioTitle: 'OUR WORK — EXAMPLES',
        portLabel1: 'FULL PAINT JOB',
        portLabel2: 'PARTIAL PAINT',
        portLabel3: 'EXAMPLE — BEFORE/AFTER',
        findTitle: 'FIND US',
        address: ' ',
        footerCopy: '© INPUT CARS | AUTO PAINTING',
        aiHeader: 'INPUT CARS ASSISTANT',
        aiWelcome: 'Hello! Ask about our painting services.',
        aiPlaceholder: 'Type here...',
        formTitle: 'BOOK PAINTING',
        namePh: 'Full Name *',
        phonePh: 'Phone *',
        emailPh: 'Email *',
        servicePh: 'Select service *',
        brandPh: 'Car brand *',
        modelPh: 'Car model *',
        descPh: 'Describe the damage — what needs painting? *',
        photoLabel: 'Add photo (damage area)',
        gdpr: 'I agree to personal data processing under GDPR.',
        submitBtn: 'Submit request',
        backBtn: '← Back',
        successTitle: 'BOOKING RECEIVED!',
        successText: 'Please wait — we will contact you shortly.',
        successCloseBtn: 'Close',
        recaptchaError: 'Please complete reCAPTCHA',
        sendError: 'Send error. Please try again.',
        sending: 'Sending...',
        fileTooBig: 'File too large (max 5 MB)',
        aiReply: 'Thanks! To book painting, click BOOK NOW.',
        svcFull: 'Full car paint',
        svcPartial: 'Partial paint',
        svcBody: 'Body repair',
        svcTouch: 'Touch-up / correction',
        svcAnticor: 'Anti-corrosion treatment',
        svcInterior: 'Interior cleaning',
        svcInteriorPromo: '🔥 Full interior dry-cleaning — PROMO -50% (only 12.07)',
        svcOther: 'Other',
        cleaningTitle: 'INTERIOR CLEANING & DRY-CLEANING',
        cleaningText: 'Thorough interior cleaning and deep dry-cleaning — restoring freshness and cleanliness to your car interior.',
        promoBadge: 'PROMO',
        promoDate: 'ONLY 12.07.2026',
        promoTitle: 'FULL INTERIOR DRY-CLEANING',
        promoDesc: 'One day, great price! Full car interior dry-cleaning with -50% discount.',
        promoOldPrice: '€60',
        promoNewPrice: '€30',
        promoDiscount: '-50%',
        promoBtn: 'BOOK THE PROMO',
        themeDark: 'Dark',
        themeLight: 'Light',
        themePaint: 'Paint',
        langPanelTitle: 'Language',
        themePanelTitle: 'Theme'
    }
};

const LANG_FLAGS = { lv: '🇱🇻', ru: '🇷🇺', et: '🇪🇪', en: '🇬🇧' };
const THEME_ICONS = { dark: 'fa-moon', light: 'fa-sun', paint: 'fa-spray-can' };

const THEMES = ['dark', 'light', 'paint'];
const THEME_LABELS = { dark: 'themeDark', light: 'themeLight', paint: 'themePaint' };

let currentLang = localStorage.getItem('inputcars-lang') || 'lv';
let currentTheme = localStorage.getItem('inputcars-theme') || 'dark';

function t(key) {
    return (I18N[currentLang] && I18N[currentLang][key]) || I18N.lv[key] || key;
}

function applyTranslations() {
    document.documentElement.lang = currentLang;
    document.title = t('pageTitle');

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (I18N[currentLang][key]) el.textContent = I18N[currentLang][key];
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(el => {
        const key = el.getAttribute('data-i18n-ph');
        if (I18N[currentLang][key]) el.placeholder = I18N[currentLang][key];
    });

    document.querySelectorAll('#langPanel button[data-lang]').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-lang') === currentLang);
    });
    const flagEl = document.getElementById('currentFlag');
    if (flagEl) flagEl.textContent = LANG_FLAGS[currentLang] || '🇱🇻';

    updateServiceOptions();
    updateThemeButtons();
}

function closeDropdowns() {
    document.querySelectorAll('.control-dropdown.open').forEach(el => el.classList.remove('open'));
}

function toggleLangPanel(e) {
    e.stopPropagation();
    const dd = document.getElementById('langDropdown');
    const wasOpen = dd.classList.contains('open');
    closeDropdowns();
    if (!wasOpen) dd.classList.add('open');
}

function toggleThemePanel(e) {
    e.stopPropagation();
    const dd = document.getElementById('themeDropdown');
    const wasOpen = dd.classList.contains('open');
    closeDropdowns();
    if (!wasOpen) dd.classList.add('open');
}

function selectLang(lang) {
    changeLang(lang);
    closeDropdowns();
}

function selectTheme(theme) {
    changeTheme(theme);
    closeDropdowns();
}

function changeLang(lang) {
    currentLang = lang;
    localStorage.setItem('inputcars-lang', lang);
    applyTranslations();
    const brand = document.getElementById('brandInput').value;
    if (brand) onBrandChange();
}

function updateServiceOptions() {
    const select = document.getElementById('serviceInput');
    const current = select.value;
    select.innerHTML = '';
    const ph = document.createElement('option');
    ph.value = '';
    ph.disabled = true;
    ph.selected = !current;
    ph.textContent = t('servicePh');
    select.appendChild(ph);
    SERVICE_KEYS.forEach(key => {
        const opt = document.createElement('option');
        opt.value = t(key);
        opt.textContent = t(key);
        if (current && opt.value === current) opt.selected = true;
        select.appendChild(opt);
    });
}

function changeTheme(theme) {
    currentTheme = theme;
    localStorage.setItem('inputcars-theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeButtons();
    const recap = document.querySelector('.g-recaptcha');
    if (recap) recap.setAttribute('data-theme', theme === 'light' ? 'light' : 'dark');
}

function cycleTheme() {
    const idx = THEMES.indexOf(currentTheme);
    changeTheme(THEMES[(idx + 1) % THEMES.length]);
}

function updateThemeButtons() {
    document.querySelectorAll('.theme-option').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-theme') === currentTheme);
    });
    const iconEl = document.getElementById('themeTriggerIcon');
    if (iconEl) {
        iconEl.className = 'fas ' + (THEME_ICONS[currentTheme] || 'fa-palette');
    }
    const metaTheme = document.querySelector('meta[name="theme-color"]');
    if (metaTheme) {
        const colors = { dark: '#050505', light: '#f0f2f5', paint: '#120a08' };
        metaTheme.content = colors[currentTheme] || '#050505';
    }
}

function openBooking() {
    document.getElementById('modal-booking').style.display = 'flex';
    document.body.style.overflow = 'hidden';
    document.querySelector('.ai-chat-widget').style.display = 'none';
}

function openBookingPromo() {
    openBooking();
    const select = document.getElementById('serviceInput');
    select.value = t('svcInteriorPromo');
}

function closeBooking() {
    document.getElementById('modal-booking').style.display = 'none';
    document.body.style.overflow = '';
    document.querySelector('.ai-chat-widget').style.display = '';
    resetForm();
}

function resetForm() {
    const form = document.getElementById('bookingForm');
    form.classList.remove('blur-effect');
    form.reset();
    document.getElementById('successPart').classList.remove('active');
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('phoneInput').value = '+371';
    document.getElementById('modelInput').innerHTML = '<option value="" disabled selected>' + t('modelPh') + '</option>';
    document.getElementById('modelInput').disabled = true;
    hideImagePreview();
    updateServiceOptions();
    if (typeof grecaptcha !== 'undefined') grecaptcha.reset();
}

function populateBrands() {
    const brandSelect = document.getElementById('brandInput');
    if (!brandSelect || brandSelect.options.length > 1) return;
    Object.keys(CAR_DATA).sort().forEach(brand => {
        const opt = document.createElement('option');
        opt.value = brand;
        opt.textContent = brand;
        brandSelect.appendChild(opt);
    });
}

function onBrandChange() {
    const brand = document.getElementById('brandInput').value;
    const modelSelect = document.getElementById('modelInput');
    modelSelect.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.disabled = true;
    placeholder.selected = true;
    placeholder.textContent = t('modelPh');
    modelSelect.appendChild(placeholder);
    if (!brand) { modelSelect.disabled = true; return; }
    CAR_DATA[brand].forEach(model => {
        const opt = document.createElement('option');
        opt.value = model;
        opt.textContent = model;
        modelSelect.appendChild(opt);
    });
    modelSelect.disabled = false;
}

function hideImagePreview() {
    document.getElementById('imagePreviewContainer').style.display = 'none';
    document.getElementById('imagePreview').src = '';
}

function setupFilePreview() {
    document.getElementById('fileInput').addEventListener('change', function () {
        const file = this.files[0];
        if (!file) { hideImagePreview(); return; }
        if (file.size > 5 * 1024 * 1024) {
            alert(t('fileTooBig'));
            this.value = '';
            hideImagePreview();
            return;
        }
        const reader = new FileReader();
        reader.onload = e => {
            document.getElementById('imagePreview').src = e.target.result;
            document.getElementById('imagePreviewContainer').style.display = 'block';
        };
        reader.readAsDataURL(file);
    });
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function showSuccess() {
    document.getElementById('bookingForm').classList.add('blur-effect');
    document.getElementById('successPart').classList.add('active');
    const bar = document.getElementById('progressBar');
    bar.style.transition = 'width 3s linear';
    bar.style.width = '100%';
    setTimeout(closeBooking, 3500);
}

async function handleSubmit(e) {
    e.preventDefault();
    let recaptchaToken = '';
    if (typeof grecaptcha !== 'undefined') {
        recaptchaToken = grecaptcha.getResponse();
        if (!recaptchaToken) { alert(t('recaptchaError')); return; }
    }
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = t('sending');
    const brand = document.getElementById('brandInput').value;
    const model = document.getElementById('modelInput').value;
    const file = document.getElementById('fileInput').files[0];
    const payload = {
        name: document.getElementById('nameInput').value.trim(),
        phone: document.getElementById('phoneInput').value.trim(),
        email: document.getElementById('emailInput').value.trim(),
        service: document.getElementById('serviceInput').value,
        carBrand: brand, carModel: model, car: `${brand} ${model}`,
        desc: document.getElementById('descInput').value.trim(),
        'g-recaptcha-response': recaptchaToken
    };
    if (file) { payload.photo = await fileToBase64(file); payload.photoName = file.name; }
    try {
        const res = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text() || t('sendError'));
        showSuccess();
    } catch (err) {
        alert(err.message || t('sendError'));
        if (typeof grecaptcha !== 'undefined') grecaptcha.reset();
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function toggleAI() {
    document.getElementById('aiWindow').classList.toggle('active');
}

function aiSend() {
    const input = document.getElementById('aiInput');
    const body = document.getElementById('aiBody');
    if (!input.value.trim()) return;
    body.innerHTML += `<p style="text-align:right;color:var(--accent-color);margin-bottom:10px;">${input.value.trim()}</p>`;
    input.value = '';
    setTimeout(() => {
        body.innerHTML += `<p style="background:var(--card-bg);padding:10px;border-radius:10px;margin-bottom:10px;">${t('aiReply')}</p>`;
        body.scrollTop = body.scrollHeight;
    }, 800);
}

document.addEventListener('DOMContentLoaded', () => {
    document.documentElement.setAttribute('data-theme', currentTheme);
    populateBrands();
    setupFilePreview();
    document.getElementById('brandInput').addEventListener('change', onBrandChange);
    document.getElementById('bookingForm').addEventListener('submit', handleSubmit);
    document.getElementById('aiInput').addEventListener('keypress', e => {
        if (e.key === 'Enter') { e.preventDefault(); aiSend(); }
    });
    document.addEventListener('click', closeDropdowns);
    document.querySelectorAll('.port-item video').forEach(video => {
        const hint = video.parentElement.querySelector('.port-play-hint');
        video.addEventListener('play', () => { if (hint) hint.style.opacity = '0'; });
        video.addEventListener('pause', () => { if (hint) hint.style.opacity = '0.9'; });
    });
    applyTranslations();
});
