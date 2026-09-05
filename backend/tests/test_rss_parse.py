from datetime import datetime, timezone

from app.services.rss.parse import parse_datetime, parse_feed
from tests.feed_fixtures import ATOM_FEED_XML, MALFORMED_FEED_XML, RSS_FEED_XML

SOURCE_URL = "https://example.com/feed.xml"


class TestParseRssFeed:
    def test_parses_items_and_maps_fields(self):
        feed = parse_feed(RSS_FEED_XML.encode(), SOURCE_URL)
        assert feed.feed_title == "Test News"
        assert feed.malformed is False
        assert feed.error is None
        assert len(feed.items) == 4

        alpha = feed.items[0]
        assert alpha.title == "Alpha emerges from stealth with new chip"
        assert alpha.url == "https://example.com/stories/alpha-chip?utm_source=rss&utm_medium=feed"
        assert alpha.summary == "Alpha announced a new processor today."
        assert alpha.author == "editor@example.com (Jane Doe)"
        assert alpha.published_at == datetime(2026, 9, 2, 9, 30, tzinfo=timezone.utc)
        assert alpha.image_url == "https://example.com/img/alpha.jpg"

    def test_resolves_relative_links_against_source_url(self):
        feed = parse_feed(RSS_FEED_XML.encode(), SOURCE_URL)
        beta = feed.items[1]
        assert beta.url == "https://example.com/stories/beta-50m"
        assert beta.image_url == "https://example.com/img/beta.jpg"

    def test_strips_html_from_cdata_summary(self):
        feed = parse_feed(RSS_FEED_XML.encode(), SOURCE_URL)
        gamma = feed.items[2]
        assert gamma.summary == "Gamma delayed the launch."

    def test_unparseable_date_becomes_none(self):
        feed = parse_feed(RSS_FEED_XML.encode(), SOURCE_URL)
        zeta = feed.items[3]
        assert zeta.published_at is None

    def test_skips_items_without_title_or_link(self):
        feed = parse_feed(RSS_FEED_XML.encode(), SOURCE_URL)
        titles = [item.title for item in feed.items]
        assert "An item with no title should be skipped entirely" not in titles


class TestParseAtomFeed:
    def test_parses_atom_entries(self):
        feed = parse_feed(ATOM_FEED_XML.encode(), "https://atoms.example.com/feed")
        assert len(feed.items) == 2
        delta = feed.items[0]
        assert delta.title == "Delta publishes whitepaper"
        assert delta.summary == "Delta released a whitepaper on cooling."
        assert delta.author == "Delta PR"
        assert delta.published_at == datetime(2026, 9, 5, 6, 0, tzinfo=timezone.utc)

    def test_offsets_normalized_to_utc(self):
        feed = parse_feed(ATOM_FEED_XML.encode(), "https://atoms.example.com/feed")
        epsilon = feed.items[1]
        assert epsilon.url == "https://atoms.example.com/posts/epsilon-update"
        assert epsilon.published_at == datetime(2026, 9, 4, 12, 30, tzinfo=timezone.utc)


class TestMalformedFeed:
    def test_marks_feed_as_error_without_items(self):
        feed = parse_feed(MALFORMED_FEED_XML, SOURCE_URL)
        assert feed.items == []
        assert feed.error is not None


class TestParseDatetime:
    def test_rfc822(self):
        assert parse_datetime("Mon, 02 Sep 2026 09:30:00 GMT") == datetime(
            2026, 9, 2, 9, 30, tzinfo=timezone.utc
        )

    def test_iso8601(self):
        assert parse_datetime("2026-09-05T06:00:00Z") == datetime(
            2026, 9, 5, 6, 0, tzinfo=timezone.utc
        )
        assert parse_datetime("2026-09-04T08:30:00-04:00") == datetime(
            2026, 9, 4, 12, 30, tzinfo=timezone.utc
        )

    def test_invalid(self):
        assert parse_datetime("NOT A REAL DATE") is None
        assert parse_datetime(None) is None
        assert parse_datetime("") is None