function escapeHtml(text) {
    return String(text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method Not Allowed' });
    }

    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
    const {
        name, phone, email, service,
        carBrand, carModel, car, desc,
        photo, photoName,
        'g-recaptcha-response': captchaResponse
    } = body;

    const secretKey = process.env.RECAPTCHA_SECRET;
    const botToken = process.env.TELEGRAM_BOT_TOKEN;
    const chatId = process.env.TELEGRAM_CHAT_ID;

    if (!botToken || !chatId) {
        return res.status(500).send('Nav iestatīts TELEGRAM_BOT_TOKEN vai TELEGRAM_CHAT_ID');
    }

    if (captchaResponse && secretKey) {
        try {
            const verifyUrl = `https://www.google.com/recaptcha/api/siteverify?secret=${secretKey}&response=${captchaResponse}`;
            const recaptchaRes = await fetch(verifyUrl, { method: 'POST' });
            const recaptchaData = await recaptchaRes.json();
            if (!recaptchaData.success) {
                return res.status(403).send('reCAPTCHA pārbaude neizdevās');
            }
        } catch {
            return res.status(403).send('reCAPTCHA kļūda');
        }
    }

    const message = `🎨 <b>JAUNS PIETEIKUMS — KRĀSOŠANA</b>\n\n`
        + `👤 <b>Klients:</b> ${escapeHtml(name)}\n`
        + `📞 <b>Tel:</b> ${escapeHtml(phone)}\n`
        + `📧 <b>E-pasts:</b> ${escapeHtml(email)}\n`
        + `🛠 <b>Pakalpojums:</b> ${escapeHtml(service)}\n`
        + `🚗 <b>Marka:</b> ${escapeHtml(carBrand)}\n`
        + `🔧 <b>Modelis:</b> ${escapeHtml(carModel)}\n`
        + `📝 <b>Apraksts:</b> ${escapeHtml(desc)}`;

    try {
        if (photo) {
            const buffer = Buffer.from(photo, 'base64');
            const formData = new FormData();
            formData.append('chat_id', chatId);
            formData.append('photo', new Blob([buffer]), photoName || 'auto-foto.jpg');
            formData.append('caption', message);
            formData.append('parse_mode', 'HTML');

            const photoRes = await fetch(`https://api.telegram.org/bot${botToken}/sendPhoto`, {
                method: 'POST',
                body: formData
            });
            const photoData = await photoRes.json();
            if (!photoData.ok) throw new Error(photoData.description || 'Telegram photo error');
        } else {
            const msgRes = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: chatId, text: message, parse_mode: 'HTML' })
            });
            const msgData = await msgRes.json();
            if (!msgData.ok) throw new Error(msgData.description || 'Telegram message error');
        }

        return res.status(200).send('Success');
    } catch (err) {
        console.error('Send error:', err.message);
        return res.status(500).send('Servera kļūda: ' + (err.message || ''));
    }
}
