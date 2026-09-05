from app.services.rss.normalize import canonicalize_url, normalize_title


class TestCanonicalizeUrl:
    def test_lowercases_scheme_and_host_without_touching_path(self):
        assert canonicalize_url("https://Example.COM/Path/Item") == "https://example.com/Path/Item"

    def test_strips_tracking_params_keeps_others(self):
        url = "https://example.com/story?a=1&utm_source=rss&utm_campaign=x&b=2"
        assert canonicalize_url(url) == "https://example.com/story?a=1&b=2"

    def test_strips_social_tracking_params(self):
        url = "https://example.com/story?fbclid=abc&gclid=def&ref=xyz"
        assert canonicalize_url(url) == "https://example.com/story"

    def test_removes_fragment(self):
        assert canonicalize_url("https://example.com/story#section") == "https://example.com/story"

    def test_strips_default_ports(self):
        assert canonicalize_url("https://example.com:443/story") == "https://example.com/story"
        assert canonicalize_url("http://example.com:80/story") == "http://example.com/story"

    def test_keeps_non_default_port(self):
        assert canonicalize_url("https://example.com:8443/story") == "https://example.com:8443/story"

    def test_root_path_keeps_slash(self):
        assert canonicalize_url("https://example.com/") == "https://example.com/"

    def test_trailing_slash_stripped_on_non_root_path(self):
        assert canonicalize_url("https://example.com/story/") == "https://example.com/story"

    def test_rejects_invalid_inputs(self):
        assert canonicalize_url(None) is None
        assert canonicalize_url("") is None
        assert canonicalize_url("   ") is None
        assert canonicalize_url("not a url") is None
        assert canonicalize_url("ftp://example.com/file") is None
        assert canonicalize_url("mailto:editor@example.com") is None

    def test_identical_after_normalization(self):
        a = canonicalize_url("https://Example.com/story?utm_source=feed")
        b = canonicalize_url("https://example.com/story")
        assert a == b


class TestNormalizeTitle:
    def test_collapses_whitespace_and_folds_case(self):
        assert normalize_title("  Hello   World  ") == "hello world"

    def test_different_casing_matches(self):
        assert normalize_title("HELLO World") == normalize_title("hello WORLD")

    def test_empty_title(self):
        assert normalize_title(None) == ""
        assert normalize_title("") == ""