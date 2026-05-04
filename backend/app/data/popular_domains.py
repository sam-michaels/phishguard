"""High-value domains commonly impersonated in phishing.

Seeds typosquatting detection. Expand iteratively as you add target verticals
(banking, crypto exchanges, SaaS, etc).
"""
POPULAR_DOMAINS: list[str] = [
    # Tech & email
    "google.com", "gmail.com", "youtube.com", "microsoft.com",
    "outlook.com", "office.com", "live.com", "apple.com",
    "icloud.com", "yahoo.com",
    # Social
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "tiktok.com", "snapchat.com", "discord.com",
    # Finance & payments
    "paypal.com", "stripe.com", "venmo.com", "wise.com",
    "coinbase.com", "binance.com", "kraken.com",
    # Banking — Canada/US (initial target market)
    "chase.com", "bankofamerica.com", "wellsfargo.com",
    "rbc.com", "td.com", "scotiabank.com", "bmo.com", "cibc.com",
    # E-commerce
    "amazon.com", "ebay.com", "etsy.com", "shopify.com",
    "walmart.com", "target.com", "costco.com",
    # Cloud / dev
    "github.com", "gitlab.com", "dropbox.com", "atlassian.com",
    "slack.com", "zoom.us", "notion.so",
    # Streaming
    "netflix.com", "spotify.com", "disneyplus.com",
]
