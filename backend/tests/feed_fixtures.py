"""Sample feed payloads for parser and ingestion tests."""

RSS_FEED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Test News</title>
    <link>https://example.com/</link>
    <item>
      <title>Alpha emerges from stealth with new chip</title>
      <link>https://example.com/stories/alpha-chip?utm_source=rss&amp;utm_medium=feed</link>
      <description>&lt;p&gt;Alpha announced a new processor &lt;b&gt;today&lt;/b&gt;.&lt;/p&gt;</description>
      <author>editor@example.com (Jane Doe)</author>
      <pubDate>Mon, 02 Sep 2026 09:30:00 GMT</pubDate>
      <media:thumbnail url="https://example.com/img/alpha.jpg" />
    </item>
    <item>
      <title>Beta raises $50M Series B</title>
      <link>/stories/beta-50m</link>
      <description>Beta secured funding.</description>
      <pubDate>Tue, 03 Sep 2026 10:00:00 +0000</pubDate>
      <enclosure url="https://example.com/img/beta.jpg" type="image/jpeg" />
    </item>
    <item>
      <description>An item with no title should be skipped entirely</description>
      <link>https://example.com/stories/no-title</link>
      <pubDate>Thu, 04 Sep 2026 08:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Gamma delays launch</title>
      <link>https://example.com/stories/gamma-delay</link>
      <description><![CDATA[<p>Gamma <em>delayed</em> the launch.</p>]]></description>
      <pubDate>Wed, 04 Sep 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Zeta teases roadmap</title>
      <link>https://example.com/stories/zeta-roadmap</link>
      <description>Zeta hinted at a roadmap.</description>
      <pubDate>NOT A REAL DATE</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM_FEED_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Test</title>
  <link href="https://atoms.example.com/"/>
  <entry>
    <title>Delta publishes whitepaper</title>
    <link href="https://atoms.example.com/posts/delta-whitepaper"/>
    <summary>Delta released a whitepaper on cooling.</summary>
    <author><name>Delta PR</name></author>
    <published>2026-09-05T06:00:00Z</published>
  </entry>
  <entry>
    <title>Epsilon ships update</title>
    <link href="/posts/epsilon-update"/>
    <published>2026-09-04T08:30:00-04:00</published>
  </entry>
</feed>
"""

DUPLICATE_TITLE_FEED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test News</title>
    <link>https://example.com/</link>
    <item>
      <title>Same Story Title</title>
      <link>https://example.com/stories/one</link>
    </item>
    <item>
      <title>Same Story Title</title>
      <link>https://example.com/stories/two</link>
    </item>
  </channel>
</rss>
"""

MALFORMED_FEED_XML = b"this is not xml <rss><open"