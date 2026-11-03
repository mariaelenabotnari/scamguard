from app.api.routes.auth_routes import login_user
from app.api.routes.narrative_routes import (
    classify_texts_batch,
    get_narrative_categories,
)
from app.core.security import LoginRateLimiter, PasswordHasher, TokenManager
from app.db.database import DatabaseManager
from app.dtos.auth_dto import LoginInputDto
from app.dtos.narrative_dto import BatchClassifyInputDto, ClassifyItemInputDto
from app.main import create_app
from app.repositories.user_repository import SqliteUserRepository
from app.services.auth_service import AuthService
from app.services.narrative_classifier_service import (
    MODEL_VERSION,
    NarrativeClassifierService,
)


def test_12_narrative_categories_batch_inference_unknown_threshold_and_model_version() -> None:
    db_manager = DatabaseManager(":memory:")
    hasher = PasswordHasher(iterations=1_000)
    token_manager = TokenManager(secret_key="narrative-test-secret")
    rate_limiter = LoginRateLimiter(max_attempts=5)
    user_repo = SqliteUserRepository(db_manager=db_manager, hasher=hasher)
    auth_service = AuthService(
        user_repo=user_repo,
        hasher=hasher,
        token_manager=token_manager,
        rate_limiter=rate_limiter,
    )
    classifier_service = NarrativeClassifierService(db_manager=db_manager)

    categories = get_narrative_categories(classifier_service=classifier_service)
    assert len(categories) == 12
    for cat in categories:
        assert cat.name
        assert cat.prototype_claim
        assert cat.severity in ("low", "medium", "high")
        assert len(cat.sub_narratives) >= 1

    admin_session = login_user(
        payload=LoginInputDto(email="elena.botnari@scamguard.md", password="scamguard2026"),
        auth_service=auth_service,
    )
    token = admin_session.access_token

    batch_input = BatchClassifyInputDto(
        confidenceThreshold=0.55,
        items=[
            ClassifyItemInputDto(
                targetId="msg-cat-01",
                targetType="message",
                text="Operațiunile pe front în Ucraina și Donbas lângă Kiev",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-02",
                targetType="message",
                text="Directiva de la Bruxelles și Uniunea Europeană în colaps",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-03",
                targetType="message",
                text="НАТО готовит военные учения у границ",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-04",
                targetType="message",
                text="Alegeri cu fraudă la secțiile de votare și guvern ilegitim",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-05",
                targetType="message",
                text="Русский язык и школы под угрозой закрытия",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-06",
                targetType="cluster",
                text="Tarifele la gaze și energie și prețurile cresc din cauza inflației",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-07",
                targetType="cluster",
                text="Приднестровье и Гагаузия в Тирасполе и Комрате",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-08",
                targetType="message",
                text="Vaccin obligatoriu impus de OMS în spital și biolab",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-09",
                targetType="message",
                text="Tradiții, familie și biserica sub atac",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-10",
                targetType="message",
                text="Meci de fotbal pe stadion și concert la teatru cu meteo bun",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-11",
                targetType="message",
                text="Băncile comerciale din Chișinău blochează retragerile de depozite și conturi",
            ),
            ClassifyItemInputDto(
                targetId="msg-cat-12",
                targetType="message",
                text="Mobilizare secretă și recrutare militară cu ordin la graniță",
            ),
            ClassifyItemInputDto(
                targetId="msg-unknown-01",
                targetType="message",
                text="Salut tuturor o zi obișnuită fără cuvinte cheie specifice",
            ),
        ],
    )

    predictions = classify_texts_batch(
        payload=batch_input,
        token=token,
        auth_service=auth_service,
        classifier_service=classifier_service,
    )
    assert len(predictions) == 13

    by_id = {p.target_id: p for p in predictions}
    assert by_id["msg-cat-01"].category == "War in Ukraine and Russia justification"
    assert by_id["msg-cat-02"].category == 'Anti-EU / "Europe is falling apart"'
    assert by_id["msg-cat-03"].category == "Anti-NATO / anti-West"
    assert by_id["msg-cat-04"].category == "Moldova government and elections delegitimisation"
    assert by_id["msg-cat-05"].category == "Russophobia, language and identity"
    assert by_id["msg-cat-06"].category == "Sanctions, energy prices and economy fear"
    assert by_id["msg-cat-07"].category == "Transnistria / Gagauzia and separatism"
    assert by_id["msg-cat-08"].category == "Health, vaccines and conspiracy"
    assert by_id["msg-cat-09"].category == "Traditional values, religion, anti-LGBT narratives"
    assert by_id["msg-cat-10"].category == "Other / not disinformation"
    assert by_id["msg-cat-10"].is_disinformation is False
    assert by_id["msg-cat-10"].fake_news_score < 0.20

    assert by_id["msg-cat-11"].category == "Financial panic, bank runs and currency devaluation"
    assert by_id["msg-cat-11"].is_disinformation is True
    assert by_id["msg-cat-11"].fake_news_score >= 0.70

    assert by_id["msg-cat-12"].category == "Forced mobilization and border militarization"
    assert by_id["msg-cat-12"].is_disinformation is True

    # Below confidence threshold returns "unknown"
    assert by_id["msg-unknown-01"].category == "unknown"
    assert by_id["msg-unknown-01"].confidence < 0.55
    assert by_id["msg-unknown-01"].is_disinformation is False

    # Every persisted prediction stores the exact model_version
    stored = classifier_service.get_prediction("msg-cat-06")
    assert stored is not None
    assert stored.model_version == MODEL_VERSION

    openapi_paths = create_app().openapi()["paths"]
    assert "/api/v1/narratives/categories" in openapi_paths
    assert "/api/v1/narratives/classify" in openapi_paths
