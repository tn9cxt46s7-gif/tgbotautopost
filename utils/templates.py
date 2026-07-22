"""Ready-made ad templates for Latvian flea markets (Rīga & LV)."""

TEMPLATES = {
    "phone": {
        "title": "📱 Telefonas / gadžets",
        "text": (
            "Pārdodu / Продаю {модель}\n"
            "Stāvoklis / Состояние: labs / labs kā jauns\n"
            "Komplekts: kārba, lādētājs\n"
            "Pilsēta: Rīga (vai Daugavpils / Liepāja)\n"
            "Cena pēc vienošanās\n"
            "Rakstiet PM / Пишите в ЛС"
        ),
    },
    "auto": {
        "title": "🚗 Auto / rezerves daļas",
        "text": (
            "Pārdodu {что}\n"
            "Gads / nobraukums: …\n"
            "Stāvoklis: …\n"
            "Pilsēta: Rīga\n"
            "Apskate uz vietas\n"
            "Cena: … €"
        ),
    },
    "clothes": {
        "title": "👕 Apģērbs / apavi",
        "text": (
            "Pārdodu {вещь}, izmērs {размер}\n"
            "Zīmols: …\n"
            "Stāvoklis: labs / jauns\n"
            "Pilsēta: Rīga\n"
            "Pašizvešana / piegāde LV"
        ),
    },
    "home": {
        "title": "🏠 Mājai / sadzīve",
        "text": (
            "Pārdodu {товар}\n"
            "Stāvoklis: darba kārtībā\n"
            "Pilsēta: Rīga / Pierīga\n"
            "Pašizvešana šodien\n"
            "Cena: … €"
        ),
    },
    "kids": {
        "title": "🧸 Bērniem",
        "text": (
            "Pārdodu {товар} bērniem\n"
            "Vecums / izmērs: …\n"
            "Stāvoklis: labs\n"
            "Pilsēta: Rīga\n"
            "Cena pēc vienošanās"
        ),
    },
}


def templates_list_text() -> str:
    lines = ["<b>Šabloni LV baraholkām</b>\nIzvēlies nišu:\n"]
    for t in TEMPLATES.values():
        lines.append(f"• <b>{t['title']}</b>")
    return "\n".join(lines)
