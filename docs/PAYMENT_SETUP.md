# Оплата EU / Латвия (EUR)

Цены и реквизиты — в **евро**. Stars остаются опциональным способом.

---

## Env (Vercel)

```env
# Канал-обязательная подписка (бот должен быть админом канала)
REQUIRED_CHANNEL=@your_channel
# если канал приватный — ссылка-приглашение:
REQUIRED_CHANNEL_URL=https://t.me/+xxxx

# Цены EUR
PAYMENT_EUR_WEEK=5
PAYMENT_EUR_MONTH=12
PAYMENT_EUR_QUARTER=29

# SEPA / карта
PAYMENT_CARD_DETAILS=IBAN: LV.. · Beneficiary: Name · Bank: Swedbank

# Другие банки (Revolut / Wise / SEB …)
PAYMENT_BANKS_OTHER=Revolut EUR · IBAN: … · Comment: order #

# Крипта вручную
PAYMENT_CRYPTO_DETAILS=USDT TRC20: …

# CryptoBot авто (фиат EUR)
CRYPTO_BOT_TOKEN=...
CRYPTO_BOT_ASSET=USDT
CRYPTO_BOT_FIAT=EUR
```

Webhook CryptoBot:
`https://ТВОЙ-ПРОЕКТ.vercel.app/cryptobot-webhook`

---

## Способы оплаты в боте

1. **SEPA / карта (EUR)** — заявка → «Я оплатил» → админ подтверждает  
2. **Другие банки (EUR)** — отдельная вкладка  
3. **CryptoBot USDT** — авто  
4. **Крипта вручную** — заявка  
5. **Telegram Stars** — опционально (не основная валюта)

После оплаты пользователь получает сообщение: **«Подписка куплена»** + дата.

---

## Языки

RU / EN / LT / ET — выбор при `/start` и в меню «Язык».

---

## Лаги

Premium custom emoji выключены по умолчанию (`USE_PREMIUM_EMOJI=0`).  
Reply-клавиатура без `icon_custom_emoji_id`.
