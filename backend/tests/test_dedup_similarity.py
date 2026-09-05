from app.services.dedup.similarity import (
    description_similarity,
    is_same_event,
    pair_score,
    title_similarity,
    token_containment,
)


class TestTitleSimilarity:
    def test_identical_normalized_titles_score_one(self):
        assert title_similarity("OpenAI Launches New Model", "openai launches new model") == 1.0

    def test_rewritten_headlines_score_high(self):
        a = "OpenAI launches GPT-5 with long context windows"
        b = "OpenAI launches GPT-5 with long context windows today"
        assert title_similarity(a, b) >= 0.85

    def test_unrelated_titles_score_low(self):
        a = "OpenAI launches a new flagship model"
        b = "Local farmers market opens downtown this weekend"
        assert title_similarity(a, b) < 0.5

    def test_empty_title_returns_zero(self):
        assert title_similarity("", "something else") == 0.0


class TestDescriptionSimilarity:
    def test_returns_none_for_short_missing_summaries(self):
        assert description_similarity("short", "also short") is None
        assert description_similarity(None, "a" * 30) is None

    def test_identical_text_returns_high_ratio(self):
        text = "The company announced the new release today during a press event."
        assert description_similarity(text, text) > 0.9


class TestTokenContainment:
    def test_full_containment_is_high(self):
        assert token_containment("OpenAI raises funding rounds", "OpenAI raises funding") >= 0.75

    def test_no_overlap_is_zero(self):
        assert token_containment("Apple pie recipes", "quantum computing advances") == 0.0


class TestIsSameEvent:
    def test_strong_title_match_alone_is_same_event(self):
        assert is_same_event(
            "OpenAI launches GPT-5 with long context windows",
            "Details about the release.",
            "OpenAI launches GPT-5 with long context windows today",
            "Other details.",
        )

    def test_weak_title_needs_matching_summary(self):
        a_title = "Anthropic unveils Claude with new features"
        b_title = "Anthropic unveils Claude with additional features"
        matching = "Both companies described the AI assistant capabilities today."
        assert is_same_event(a_title, matching, b_title, matching)

    def test_disjoint_titles_not_same_event(self):
        assert not is_same_event(
            "City council approves new budget",
            "The budget was approved after a long session.",
            "Tech startup raises millions in funding round",
            "The startup secured funding from multiple investors.",
        )


class TestPairScore:
    def test_score_between_zero_and_one(self):
        score = pair_score(
            "OpenAI launches new model", "Long summary here about the model release.",
            "OpenAI launches updated model", "Another long summary describing the release.",
        )
        assert 0.0 <= score <= 1.0