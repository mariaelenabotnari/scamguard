"""Comprehensive unit test suite for TextNormaliser v2 (three views and language/script detection).
Includes at least 40 real-looking Romanian, Russian, and mixed Telegram examples.
"""

from app.services.text_normaliser import TextNormaliser

TEST_CASES_RO = [
    ("Tariful la gazele naturale va crește cu 35% de la 1 decembrie conform ANRE.", "RO"),
    (
        "Prețurile la energia electrică explodează în toată Republica Moldova săptămâna viitoare.",
        "RO",
    ),
    (
        "Guvernul de la Chișinău pregătește noi măsuri de sprijin pentru consumatorii vulnerabili.",
        "RO",
    ),
    ("Fermierii moldoveni au blocat punctul de trecere a frontierei de la Leușeni.", "RO"),
    (
        "Cetățenii din diaspora vor putea vota la peste 200 de secții de votare deschise în UE.",
        "RO",
    ),
    (
        "Ministrul Energiei a declarat că stocurile de gaze naturale sunt suficiente pentru iarnă.",
        "RO",
    ),
    ("În raionul Orhei au fost inaugurate trei grădinițe renovate cu sprijin extern.", "RO"),
    (
        "Poliția de Frontieră anunță trafic intens la vama Sculeni pe sensul de ieșire din țară.",
        "RO",
    ),
    ("Banca Națională a Moldovei a menținut rata de bază la nivelul de 3.6% pe an.", "RO"),
    (
        "Spitalul Republican a primit un lot modern de echipamente medicale.",
        "RO",
    ),
    (
        "Primăria municipiului Bălți a aprobat bugetul local pentru anul viitor în a doua lectură.",
        "RO",
    ),
    (
        "Protest pașnic în fața Parlamentului organizat de asociațiile de producători agricoli.",
        "RO",
    ),
    ("Serviciul Vamal a raportat încasări record la bugetul de stat pentru luna octombrie.", "RO"),
    ("Echipa națională de fotbal a Moldovei a remizat în meciul din Liga Națiunilor.", "RO"),
    ("Comisia Electorală Centrală a tipărit buletinele de vot pentru primul tur de scrutin.", "RO"),
]

TEST_CASES_RU = [
    ("Тариф на природный газ вырастет на 35% с 1 декабря по решению регулятора.", "RU"),
    ("Цены на электроэнергию снова резко вырастут в Молдове со следующей недели.", "RU"),
    ("Правительство в Кишиневе готовит новые компенсации для уязвимых потребителей.", "RU"),
    ("Аграрии вывели сельхозтехнику и заблокировали контрольно-пропускной пункт Леушены.", "RU"),
    ("Избирательные участки в европейских странах готовы к проведению голосования.", "RU"),
    (
        "Минэнерго заверяет, что запасов природного газа хватит на отопительный сезон.",
        "RU",
    ),
    ("В Комрате состоялось заседание Народного собрания Гагаузии по бюджетным вопросам.", "RU"),
    ("Таможенная служба Молдовы предупреждает об очередях на КПП Скуляны.", "RU"),
    ("Национальный банк Молдовы сохранил базовую процентную ставку без изменений.", "RU"),
    ("В Бельцах завершился капитальный ремонт главного моста через реку Реут.", "RU"),
    ("Полиция Кишинева усилила патрулирование центральных улиц города во время праздников.", "RU"),
    (
        "Фермеры требуют от министерства сельского хозяйства прямых выплат за понесенный ущерб.",
        "RU",
    ),
    ("ЦИК Молдовы завершил аккредитацию международных наблюдателей на выборах.", "RU"),
    ("В Тирасполе прошла встреча рабочих групп по вопросам железнодорожного сообщения.", "RU"),
    ("В субботу в Национальном театре оперы и балета состоится открытие осеннего сезона.", "RU"),
]

TEST_CASES_MIXED = [
    (
        "Breaking: В Кишиневе начались proteste ale fermierilor la vama Leușeni cu tehnică grea.",
        "MIXED",
    ),
    (
        "Comrat / Комрат: Guvernul a alocat fonduri speciale для поддержки местных аграриев.",
        "MIXED",
    ),
    ("Atenție șoferi! На трассе M1 Chisinau-Leuseni движение заблокировано из-за ДТП.", "MIXED"),
    (
        "Facturile la energie / Новые тарифы на газ: Chișinăul și Tiraspolul negociază контракт.",
        "MIXED",
    ),
    (
        "CEC Moldova / ЦИК: Rezultatele preliminare ale alegerilor după подсчета 90% бюллетеней.",
        "MIXED",
    ),
]

TEST_CASES_DIACRITICS_AND_FORMATS = [
    # Cedillas vs modern commas
    ("Ştiri de ultimă oră din Chişinău privind preţurile la energie electrică.", "RO"),
    ("În şcolile din ţară a început vacanţa de toamnă a elevilor.", "RO"),
    ("Guvernul a anunţat măsuri de sprijin pentru agricultorii din raioanele de sud.", "RO"),
    ("Toţi cetăţenii sunt aşteptaţi la vot duminică între orele 07:00 şi 21:00.", "RO"),
    ("Preşedintele ţării a semnat decretul de promulgare a noii legi fiscale.", "RO"),
]


def test_text_normaliser_multi_view_and_properties() -> None:
    normaliser = TextNormaliser()
    raw = (
        "Breaking! Vezi detalii pe https://t.me/moldova_live/1234 sau contactează @admin_md: "
        "Tariful la gaz crește cu 35%!"
    )

    dto = normaliser.normalise(raw)

    # 1. Display text preserves original exact characters
    assert dto.text_display == raw

    # 2. Model text removes URLs and handles, preserves case and numbers
    assert "https://t.me" not in dto.text_model
    assert "@admin_md" not in dto.text_model
    assert "Tariful la gaz crește cu 35%!" in dto.text_model

    # 3. Hash text lowercases, strips punctuation, normalises diacritics
    assert "35" in dto.normalised_text
    assert "crește" in dto.normalised_text
    assert "!" not in dto.normalised_text
    assert ":" not in dto.normalised_text
    assert len(dto.text_hash) == 64

    # Backwards compatibility
    assert dto.language == "RO"
    assert not dto.is_mixed_script


def test_text_normaliser_40_plus_bilingual_examples() -> None:
    normaliser = TextNormaliser()
    total_evaluated = 0

    # 1. Romanian examples
    for text, expected_lang in TEST_CASES_RO:
        dto = normaliser.normalise(text)
        assert dto.language == expected_lang, f"Failed on RO: {text}"
        assert len(dto.normalised_text) > 0
        assert len(dto.text_model) > 0
        assert dto.text_display == text
        assert not dto.is_mixed_script
        total_evaluated += 1

    # 2. Russian examples (must preserve native Cyrillic in text_model)
    for text, expected_lang in TEST_CASES_RU:
        dto = normaliser.normalise(text)
        assert dto.language == expected_lang, f"Failed on RU: {text}"
        # Native Cyrillic MUST be preserved in text_model for transformer models
        assert any("\u0400" <= ch <= "\u04ff" for ch in dto.text_model)
        assert dto.text_display == text
        assert not dto.is_mixed_script
        total_evaluated += 1

    # 3. Mixed script examples
    for text, expected_lang in TEST_CASES_MIXED:
        dto = normaliser.normalise(text)
        assert dto.language == expected_lang, f"Failed on MIXED: {text}"
        assert dto.is_mixed_script is True
        total_evaluated += 1

    # 4. Cedilla vs Comma unification examples
    for text, expected_lang in TEST_CASES_DIACRITICS_AND_FORMATS:
        dto = normaliser.normalise(text)
        assert dto.language == expected_lang
        # In hash view, cedillas are flattened to commas/ASCII for signature robustness
        assert "ş" not in dto.normalised_text
        assert "ţ" not in dto.normalised_text
        total_evaluated += 1

    assert total_evaluated >= 40, f"Expected at least 40 examples, got {total_evaluated}"


def test_text_normaliser_handles_short_and_empty() -> None:
    normaliser = TextNormaliser()
    empty_dto = normaliser.normalise("")
    assert empty_dto.normalised_text == ""
    assert empty_dto.text_model == ""
    assert len(empty_dto.text_hash) == 64
    assert empty_dto.language == "OTHER"

    short_ro = normaliser.normalise("Gaz ieftin")
    assert short_ro.normalised_text == "gaz ieftin"
    assert short_ro.language == "RO"
