#!/usr/bin/env python3
"""Generate simple Latvian sale contract + receipt PDFs."""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


class Doc(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", size=8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"Lapa {self.page_no()}/{{nb}}", align="C")


def make_pdf() -> Doc:
    pdf = Doc(format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_font("DejaVu", "", FONT_REG)
    pdf.add_font("DejaVu", "B", FONT_BOLD)
    pdf.set_margins(16, 14, 16)
    return pdf


def h1(pdf: Doc, text: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "B", 14)
    pdf.set_text_color(11, 61, 46)
    pdf.multi_cell(0, 7, text, align="C")
    pdf.ln(1)


def h2(pdf: Doc, text: str):
    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 6, text)
    pdf.ln(0.5)


def body(pdf: Doc, text: str, bold: bool = False):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "B" if bold else "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 5, text)
    pdf.ln(0.8)


def blank_line(pdf: Doc, label: str):
    body(pdf, f"{label} ______________________________________")


def signature_block(pdf: Doc):
    pdf.ln(6)
    y = pdf.get_y()
    col_w = 85
    gap = 8

    pdf.set_font("DejaVu", "B", 10)
    pdf.set_xy(16, y)
    pdf.multi_cell(col_w, 5, "PĀRDEVĒJS")
    pdf.set_font("DejaVu", "", 10)
    pdf.set_x(16)
    pdf.multi_cell(col_w, 5, "Emils Basarovs\nPersonas kods: 010807-21646\n\n\n____________________________\nParaksts / datums")

    pdf.set_font("DejaVu", "B", 10)
    pdf.set_xy(16 + col_w + gap, y)
    pdf.multi_cell(col_w, 5, "PIRCĒJS")
    pdf.set_font("DejaVu", "", 10)
    pdf.set_xy(16 + col_w + gap, y + 5)
    pdf.multi_cell(
        col_w,
        5,
        "Vārds, uzvārds: ________________\n"
        "Personas kods: ________________\n\n\n"
        "____________________________\n"
        "Paraksts / datums",
    )


def write_contract(path: Path):
    pdf = make_pdf()
    pdf.add_page()

    h1(pdf, "PIRKUMA–PĀRDEVUMA LĪGUMS")
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "Nr. 2026-07-22/1", align="C")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "Noslēgts: 2026. gada ____. _____________, Rīgā / Latvijā", align="C")
    pdf.ln(3)

    body(
        pdf,
        "Pārdevējs: Emils Basarovs, personas kods 010807-21646, "
        "adrese: ________________________________, tālrunis: ________________ "
        "(turpmāk – Pārdevējs), no vienas puses, un",
    )
    body(
        pdf,
        "Pircējs: ________________________________, personas kods _______________, "
        "adrese: ________________________________, tālrunis: ________________ "
        "(turpmāk – Pircējs), no otras puses,",
    )
    body(
        pdf,
        "abi kopā saukti – Puses, noslēdz šo pirkuma–pārdevuma līgumu (turpmāk – Līgums) "
        "par turpmāk minēto:",
    )

    h2(pdf, "1. Līguma priekšmets")
    body(
        pdf,
        "1.1. Pārdevējs pārdod, bet Pircējs pērk un apņemas pieņemt un apmaksāt šādu lietu "
        "(turpmāk – Prece):",
    )
    body(
        pdf,
        "Nosaukums: Mehāniskā tastatūra AJAZZ × NACODEX (AK820 MAX tipa / «Jaunā paaudze»)\n"
        "Apraksts: Kompakta mehāniskā tastatūra (~75%), magnētiskie slēdži, "
        "krāsu shēma violeta/balta ar ziliem akcentiem, ar rotējošu vadības ripu. "
        "Ražots Ķīnā. Stāvoklis: lietots, vizuāli labs.\n"
        "Svītrkods: 6976412962583\n"
        "Daudzums: 1 (viens) gabals\n"
        "Cena: 43,08 EUR (četrdesmit trīs eiro un 08 centi)",
    )
    body(
        pdf,
        "1.2. Prece tiek pārdota kā lietota privātpersonu darījuma ietvaros. Pircējs "
        "apliecina, ka pirms Līguma noslēgšanas ir apskatījis Preci (vai tās fotogrāfijas) "
        "un piekrīt tās faktiskajam stāvoklim.",
    )

    h2(pdf, "2. Cena un norēķinu kārtība")
    body(pdf, "2.1. Preces cena ir 43,08 EUR.")
    body(
        pdf,
        "2.2. Pircējs samaksā Preces cenu: [ ] skaidrā naudā  /  [ ] ar bankas pārskaitījumu  "
        "/  [ ] cits: ____________",
    )
    body(
        pdf,
        "2.3. Samaksas saņemšanu Pārdevējs apliecina ar kvīti Nr. 2026-07-22/1-K un/vai ar "
        "abpusējiem parakstiem uz šī Līguma.",
    )
    body(
        pdf,
        "2.4. Īpašuma tiesības uz Preci pāriet Pircējam ar brīdi, kad ir saņemta pilna "
        "samaksa un Prece ir nodota Pircējam.",
    )

    h2(pdf, "3. Preces nodošana")
    body(
        pdf,
        "3.1. Prece tiek nodota Pircējam: 2026. gada ____. _____________, "
        "vietā: ________________________________.",
    )
    body(
        pdf,
        "3.2. Nodošanas brīdī Pircējs pārbauda Preces komplektāciju un ārējo stāvokli. "
        "Parakstot Līgumu / kvīti, Pircējs apliecina, ka Preci ir pieņēmis bez iebildumiem "
        "(ja vien nav rakstiski norādīts citādi).",
    )

    h2(pdf, "4. Pušu apliecinājumi un «uzticības garantija»")
    body(
        pdf,
        "4.1. Pārdevējs apliecina, ka Prece ir viņa īpašumā, nav ieķīlāta, nav apgrūtināta "
        "ar trešo personu tiesībām un ka Pārdevējam ir tiesības to pārdot.",
    )
    body(
        pdf,
        "4.2. Pārdevējs apliecina, ka viņam zināmo robežās Prece ir darba kārtībā un "
        "atbilst šajā Līgumā norādītajam aprakstam.",
    )
    body(
        pdf,
        "4.3. Tā kā darījums notiek starp privātpersonām un Prece ir lietota, ražotāja "
        "vai veikala garantija netiek nodota, ja vien Puses rakstiski nevienojas citādi.",
    )
    body(
        pdf,
        "4.4. Uzticības (labticības) garantija: 14 (četrpadsmit) dienu laikā no Preces "
        "nodošanas, ja tiek konstatēts būtisks slēpts defekts, kas pastāvēja jau nodošanas "
        "brīdī un par kuru Pircējs nevarēja zināt, Puses labticīgi vienojas par: "
        "(a) Preces labošanu; (b) daļēju cenas atmaksu; vai (c) darījuma atcelšanu un "
        "Preces atgriešanu pret pilnu cenas atmaksu. Mehāniski bojājumi, kas radušies "
        "pēc nodošanas, kā arī normāls nolietojums, šo punktu neaptver.",
    )
    body(
        pdf,
        "4.5. Šis Līgums kalpo kā abpusējs rakstisks pierādījums par darījuma faktu, "
        "cenu, Preces identifikāciju un nodošanu.",
    )

    h2(pdf, "5. Atbildība un strīdu izšķiršana")
    body(
        pdf,
        "5.1. Puses ir atbildīgas par Līguma saistību izpildi saskaņā ar Latvijas "
        "Republikas normatīvajiem aktiem, tostarp Civillikumu.",
    )
    body(
        pdf,
        "5.2. Strīdus Puses vispirms cenšas atrisināt sarunu ceļā. Ja vienošanās "
        "netiek panākta, strīds izšķirams Latvijas Republikas tiesā pēc piekritības.",
    )

    h2(pdf, "6. Noslēguma noteikumi")
    body(
        pdf,
        "6.1. Līgums stājas spēkā ar tā parakstīšanas brīdi un ir spēkā līdz saistību "
        "pilnīgai izpildei.",
    )
    body(
        pdf,
        "6.2. Līgums sastādīts latviešu valodā 2 (divos) eksemplāros ar vienādu "
        "juridisko spēku, pa vienam eksemplāram katrai Pusei.",
    )
    body(pdf, "6.3. Līguma pielikums: kvīts Nr. 2026-07-22/1-K.")

    signature_block(pdf)
    pdf.output(path)


def write_receipt(path: Path):
    pdf = make_pdf()
    pdf.add_page()

    h1(pdf, "KVĪTS")
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "Maksājuma un Preces nodošanas apliecinājums", align="C")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "Nr. 2026-07-22/1-K", align="C")
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "Datums: ____.________.2026    Vieta: _______________", align="C")
    pdf.ln(4)

    body(pdf, "Saņēmējs (Pārdevējs): Emils Basarovs", bold=True)
    body(pdf, "Personas kods: 010807-21646")
    blank_line(pdf, "Adrese:")
    blank_line(pdf, "Tālrunis:")
    pdf.ln(2)

    body(
        pdf,
        "Es, Emils Basarovs, personas kods 010807-21646, ar šo apliecinu, ka esmu "
        "saņēmis no Pircēja ________________________________ (personas kods: _______________) "
        "naudas summu:",
    )

    # Simple table as text block
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_fill_color(238, 242, 239)
    pdf.cell(12, 7, "Nr.", border=1, fill=True)
    pdf.cell(108, 7, "Prece", border=1, fill=True)
    pdf.cell(18, 7, "Gab.", border=1, fill=True, align="C")
    pdf.cell(22, 7, "Cena", border=1, fill=True, align="R")
    pdf.cell(22, 7, "Summa", border=1, fill=True, align="R")
    pdf.ln()

    pdf.set_font("DejaVu", "", 9)
    x = pdf.get_x()
    y = pdf.get_y()
    row_h = 22
    pdf.multi_cell(12, row_h, "1", border=1, align="C")
    pdf.set_xy(x + 12, y)
    pdf.multi_cell(
        108,
        5.5,
        "Mehāniskā tastatūra AJAZZ × NACODEX (AK820 MAX tipa),\n"
        "magnētiskie slēdži, violeta/balta, svītrkods 6976412962583.\n"
        "Lietota. Līgums Nr. 2026-07-22/1.",
        border=1,
    )
    # align other cells to same row height
    pdf.set_xy(x + 120, y)
    pdf.cell(18, row_h, "1", border=1, align="C")
    pdf.cell(22, row_h, "43,08", border=1, align="R")
    pdf.cell(22, row_h, "43,08", border=1, align="R")
    pdf.ln(row_h)

    pdf.set_font("DejaVu", "B", 11)
    pdf.set_fill_color(238, 242, 239)
    pdf.cell(160, 8, "Kopā saņemts", border=1, fill=True, align="R")
    pdf.cell(22, 8, "43,08 EUR", border=1, fill=True, align="R")
    pdf.ln(10)

    body(pdf, "Summa vārdiem: četrdesmit trīs eiro un 08 centi.", bold=True)
    body(
        pdf,
        "Maksājuma veids:  [ ] skaidrā naudā   [ ] bankas pārskaitījums   [ ] cits: ________",
    )
    body(
        pdf,
        "Prece nodota Pircējam:  [ ] jā, pilnā komplektācijā   [ ] citādi: ________________",
    )
    body(
        pdf,
        "Pircējs apliecina, ka Preci ir pārbaudījis un pieņēmis bez iebildumiem "
        "(ja vien nav norādīts citādi): ________________________________________________",
    )

    signature_block(pdf)

    pdf.ln(28)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0,
        4,
        "Šī kvīts ir pirkuma–pārdevuma līguma Nr. 2026-07-22/1 pielikums. "
        "Dokuments nav PVN rēķins (privātpersonu darījums). Saglabājiet kopiju abām pusēm.",
    )

    pdf.output(path)


def write_txt(path: Path):
    text = """\
================================================================================
PIRKUMA–PĀRDEVUMA LĪGUMS  Nr. 2026-07-22/1
================================================================================
Noslēgts: 2026. gada ____. _____________, Rīgā / Latvijā

PĀRDEVĒJS: Emils Basarovs, personas kods 010807-21646
Adrese: ________________________________  Tālrunis: ________________

PIRCĒJS: ________________________________, personas kods _______________
Adrese: ________________________________  Tālrunis: ________________

1. LĪGUMA PRIEKŠMETS
Pārdevējs pārdod, Pircējs pērk:
  Nosaukums:  Mehāniskā tastatūra AJAZZ × NACODEX (AK820 MAX tipa)
  Apraksts:   Magnētiskie slēdži, violeta/balta, ~75% izkārtojums
  Svītrkods:  6976412962583
  Daudzums:   1 gab.
  Cena:       43,08 EUR (četrdesmit trīs eiro un 08 centi)
  Stāvoklis:  lietots, vizuāli labs

2. NORĒĶINI
Maksājuma veids: [ ] skaidrā naudā  [ ] bankas pārskaitījums  [ ] cits: ______
Īpašuma tiesības pāriet pēc pilnas samaksas un Preces nodošanas.

3. NODOŠANA
Datums: 2026. gada ____. _____________   Vieta: ____________________________
Pircējs pārbauda Preci nodošanas brīdī.

4. UZTICĪBAS GARANTIJA (14 dienas)
Ja 14 dienu laikā tiek konstatēts būtisks slēpts defekts, kas pastāvēja jau
nodošanas brīdī, Puses labticīgi vienojas par labošanu, daļēju atmaksu vai
darījuma atcelšanu. Bojājumi pēc nodošanas / nolietojums neietilpst.

5. STRĪDI
Saskaņā ar Latvijas Republikas Civillikumu; vispirms sarunas, tad tiesa.

6. NOSLĒGUMS
Līgums 2 eksemplāros. Pielikums: kvīts Nr. 2026-07-22/1-K.


PĀRDEVĒJS                          PIRCĒJS
Emils Basarovs                     ____________________________
PK: 010807-21646                   PK: ________________________

________________________           ____________________________
Paraksts / datums                  Paraksts / datums


================================================================================
KVĪTS  Nr. 2026-07-22/1-K
================================================================================
Datums: ____.________.2026     Vieta: _______________

Saņēmējs: Emils Basarovs, personas kods 010807-21646

Saņemts no Pircēja: ________________________________ (PK: _______________)

Prece: AJAZZ × NACODEX tastatūra, svītrkods 6976412962583
Daudzums: 1    Cena: 43,08 EUR    KOPĀ: 43,08 EUR
Summa vārdiem: četrdesmit trīs eiro un 08 centi

Maksājums: [ ] skaidrā naudā  [ ] pārskaitījums  [ ] cits: ______
Prece nodota: [ ] jā

PĀRDEVĒJS                          PIRCĒJS
________________________           ____________________________
Paraksts / datums                  Paraksts / datums
"""
    path.write_text(text, encoding="utf-8")


def main():
    write_contract(OUT / "pirkuma-pardevuma-ligums.pdf")
    write_receipt(OUT / "kvits.pdf")
    write_txt(OUT / "ligums-un-kvits.txt")
    print("OK:", OUT / "pirkuma-pardevuma-ligums.pdf")
    print("OK:", OUT / "kvits.pdf")
    print("OK:", OUT / "ligums-un-kvits.txt")


if __name__ == "__main__":
    main()
