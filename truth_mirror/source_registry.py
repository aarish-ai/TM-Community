SOURCE_REGISTRY = {
    "reuters.com":        {"name": "Reuters",           "category": "wire_service",   "country": "International", "alignment": "western",      "tier": 1},
    "apnews.com":         {"name": "AP News",            "category": "wire_service",   "country": "International", "alignment": "western",      "tier": 1},
    "bbc.com":            {"name": "BBC",                "category": "western_msm",    "country": "UK",            "alignment": "western",      "tier": 1},
    "bbc.co.uk":          {"name": "BBC",                "category": "western_msm",    "country": "UK",            "alignment": "western",      "tier": 1},
    "theguardian.com":    {"name": "The Guardian",       "category": "western_msm",    "country": "UK",            "alignment": "western",      "tier": 1},
    "nytimes.com":        {"name": "New York Times",     "category": "western_msm",    "country": "USA",           "alignment": "western",      "tier": 1},
    "washingtonpost.com": {"name": "Washington Post",    "category": "western_msm",    "country": "USA",           "alignment": "western",      "tier": 1},
    "cnn.com":            {"name": "CNN",                "category": "western_msm",    "country": "USA",           "alignment": "western",      "tier": 2},
    "foxnews.com":        {"name": "Fox News",           "category": "western_msm",    "country": "USA",           "alignment": "western",      "tier": 2},
    "politico.com":       {"name": "Politico",           "category": "western_msm",    "country": "USA",           "alignment": "western",      "tier": 2},
    "france24.com":       {"name": "France 24",          "category": "western_msm",    "country": "France",        "alignment": "western",      "tier": 2},
    "dw.com":             {"name": "Deutsche Welle",     "category": "western_msm",    "country": "Germany",       "alignment": "western",      "tier": 2},
    "aljazeera.com":      {"name": "Al Jazeera",         "category": "gulf_media",     "country": "Qatar",         "alignment": "gulf",         "tier": 2},
    "alarabiya.net":      {"name": "Al Arabiya",         "category": "gulf_media",     "country": "Saudi Arabia",  "alignment": "gulf",         "tier": 2},
    "arabnews.com":       {"name": "Arab News",          "category": "gulf_media",     "country": "Saudi Arabia",  "alignment": "gulf",         "tier": 2},
    "tass.com":           {"name": "TASS",               "category": "state_media",    "country": "Russia",        "alignment": "eastern",      "tier": 2},
    "rt.com":             {"name": "RT",                 "category": "state_media",    "country": "Russia",        "alignment": "eastern",      "tier": 3},
    "cgtn.com":           {"name": "CGTN",               "category": "state_media",    "country": "China",         "alignment": "eastern",      "tier": 2},
    "xinhuanet.com":      {"name": "Xinhua",             "category": "state_media",    "country": "China",         "alignment": "eastern",      "tier": 2},
    "globaltimes.cn":     {"name": "Global Times",       "category": "state_media",    "country": "China",         "alignment": "eastern",      "tier": 3},
    "presstv.ir":         {"name": "Press TV",           "category": "state_media",    "country": "Iran",          "alignment": "iran",         "tier": 3},
    "irna.ir":            {"name": "IRNA",               "category": "state_media",    "country": "Iran",          "alignment": "iran",         "tier": 2},
    "timesofisrael.com":  {"name": "Times of Israel",    "category": "regional_media", "country": "Israel",        "alignment": "israel",       "tier": 2},
    "haaretz.com":        {"name": "Haaretz",            "category": "regional_media", "country": "Israel",        "alignment": "israel",       "tier": 2},
    "jpost.com":          {"name": "Jerusalem Post",     "category": "regional_media", "country": "Israel",        "alignment": "israel",       "tier": 2},
    "dawn.com":           {"name": "Dawn",               "category": "regional_media", "country": "Pakistan",      "alignment": "south_asian",  "tier": 2},
    "geo.tv":             {"name": "Geo TV",             "category": "regional_media", "country": "Pakistan",      "alignment": "south_asian",  "tier": 2},
    "thehindu.com":       {"name": "The Hindu",          "category": "regional_media", "country": "India",         "alignment": "south_asian",  "tier": 2},
    "middleeasteye.net":  {"name": "Middle East Eye",    "category": "independent",    "country": "UK",            "alignment": "independent",  "tier": 2},
    "theintercept.com":   {"name": "The Intercept",      "category": "independent",    "country": "USA",           "alignment": "independent",  "tier": 2},
    "bellingcat.com":     {"name": "Bellingcat",         "category": "osint",          "country": "International", "alignment": "independent",  "tier": 1},
    "en.wikipedia.org":   {"name": "Wikipedia",          "category": "encyclopedia",   "country": "International", "alignment": "neutral",      "tier": 3},
    "asia.nikkei.com":    {"name": "Nikkei Asia",        "category": "business",       "country": "Japan",         "alignment": "independent",  "tier": 1},
    "japantimes.co.jp":   {"name": "The Japan Times",    "category": "regional_media", "country": "Japan",         "alignment": "independent",  "tier": 2},
    "english.kyodonews.net":{"name": "Kyodo News",       "category": "wire_service",   "country": "Japan",         "alignment": "neutral",      "tier": 1},
    "en.yna.co.kr":       {"name": "Yonhap News Agency", "category": "wire_service",   "country": "South Korea",   "alignment": "neutral",      "tier": 2},
    "channelnewsasia.com":{"name": "CNA",                "category": "regional_media", "country": "Singapore",     "alignment": "neutral",      "tier": 2},
    "scmp.com":           {"name": "South China Morning Post", "category": "regional_media", "country": "Hong Kong", "alignment": "independent", "tier": 2},
    "tribune.com.pk":     {"name": "The Express Tribune","category": "regional_media", "country": "Pakistan",      "alignment": "south_asian",  "tier": 2},
    "theprint.in":        {"name": "The Print",          "category": "regional_media", "country": "India",         "alignment": "south_asian",  "tier": 2},
    "hindustantimes.com": {"name": "Hindustan Times",    "category": "regional_media", "country": "India",         "alignment": "south_asian",  "tier": 2},
    "thedailystar.net":   {"name": "The Daily Star",     "category": "regional_media", "country": "Bangladesh",    "alignment": "south_asian",  "tier": 2},
    "republicworld.com":  {"name": "Republic World",     "category": "regional_media", "country": "India",         "alignment": "south_asian",  "tier": 3},
    "ndtv.com":           {"name": "NDTV",               "category": "regional_media", "country": "India",         "alignment": "south_asian",  "tier": 2},
    "thejakartapost.com": {"name": "The Jakarta Post",   "category": "regional_media", "country": "Indonesia",     "alignment": "independent",  "tier": 2},
    "bangkokpost.com":    {"name": "Bangkok Post",       "category": "regional_media", "country": "Thailand",      "alignment": "independent",  "tier": 2},
    "rappler.com":        {"name": "Rappler",            "category": "regional_media", "country": "Philippines",   "alignment": "independent",  "tier": 2},
    "inquirer.net":       {"name": "Philippine Daily Inquirer", "category": "regional_media", "country": "Philippines", "alignment": "independent", "tier": 2},
    "vietnamnet.vn":      {"name": "VietnamNet",         "category": "state_media",    "country": "Vietnam",       "alignment": "eastern",      "tier": 2},
    "al-monitor.com":     {"name": "Al-Monitor",         "category": "regional_media", "country": "International", "alignment": "independent",  "tier": 2},
    "thenationalnews.com":{"name": "The National",       "category": "gulf_media",     "country": "UAE",           "alignment": "gulf",         "tier": 2},
    "iranintl.com":       {"name": "Iran International", "category": "independent",    "country": "UK",            "alignment": "independent",  "tier": 3},
    "tehrantimes.com":    {"name": "Tehran Times",       "category": "state_media",    "country": "Iran",          "alignment": "iran",         "tier": 3},
    "themoscowtimes.com": {"name": "The Moscow Times",   "category": "independent",    "country": "Netherlands",   "alignment": "independent",  "tier": 2},
    "meduza.io":          {"name": "Meduza",             "category": "independent",    "country": "Latvia",        "alignment": "independent",  "tier": 1},
    "novayagazeta.eu":    {"name": "Novaya Gazeta Europe","category": "independent",   "country": "Latvia",        "alignment": "independent",  "tier": 1},
    "kyivindependent.com":{"name": "The Kyiv Independent","category": "independent",   "country": "Ukraine",       "alignment": "independent",  "tier": 2},
    "kyivpost.com":       {"name": "Kyiv Post",          "category": "independent",    "country": "Ukraine",       "alignment": "independent",  "tier": 2},
    "balkaninsight.com":  {"name": "Balkan Insight",     "category": "independent",    "country": "International", "alignment": "independent",  "tier": 2},
    "dailymaverick.co.za":{"name": "Daily Maverick",     "category": "independent",    "country": "South Africa",  "alignment": "independent",  "tier": 2},
    "mg.co.za":           {"name": "Mail & Guardian",    "category": "independent",    "country": "South Africa",  "alignment": "independent",  "tier": 2},
    "premiumtimesng.com": {"name": "Premium Times",      "category": "independent",    "country": "Nigeria",       "alignment": "independent",  "tier": 2},
    "thecontinent.org":   {"name": "The Continent",      "category": "independent",    "country": "South Africa",  "alignment": "independent",  "tier": 2},
    "allafrica.com":      {"name": "allAfrica.com",      "category": "wire_service",   "country": "International", "alignment": "neutral",      "tier": 2},
    "africanews.com":     {"name": "AfricaNews",         "category": "regional_media", "country": "France",        "alignment": "neutral",      "tier": 2},
    "en.mercopress.com":  {"name": "MercoPress",         "category": "independent",    "country": "Uruguay",       "alignment": "independent",  "tier": 2},
    "batimes.com.ar":     {"name": "Buenos Aires Times", "category": "independent",    "country": "Argentina",     "alignment": "independent",  "tier": 2},
    "folha.uol.com.br":   {"name": "Folha de S.Paulo",   "category": "independent",    "country": "Brazil",        "alignment": "independent",  "tier": 2},
    "insightcrime.org":   {"name": "InSight Crime",      "category": "osint",          "country": "International", "alignment": "independent",  "tier": 1},
    "telesurenglish.net": {"name": "teleSUR English",    "category": "state_media",    "country": "Venezuela",     "alignment": "eastern",      "tier": 3},
    "occrp.org":          {"name": "OCCRP",              "category": "osint",          "country": "International", "alignment": "independent",  "tier": 1},
    "opendemocracy.net":  {"name": "openDemocracy",      "category": "independent",    "country": "UK",            "alignment": "independent",  "tier": 2},
}

PUBLISHER_NAME_MAP = {
    "al jazeera":       {"name": "Al Jazeera",      "category": "gulf_media",   "country": "Qatar",         "alignment": "gulf",        "tier": 2},
    "tass":             {"name": "TASS",             "category": "state_media",  "country": "Russia",        "alignment": "eastern",     "tier": 2},
    "cgtn":             {"name": "CGTN",             "category": "state_media",  "country": "China",         "alignment": "eastern",     "tier": 2},
    "xinhua":           {"name": "Xinhua",           "category": "state_media",  "country": "China",         "alignment": "eastern",     "tier": 2},
    "dawn pk":          {"name": "Dawn",             "category": "regional_media","country": "Pakistan",     "alignment": "south_asian", "tier": 2},
    "dawn":             {"name": "Dawn",             "category": "regional_media","country": "Pakistan",     "alignment": "south_asian", "tier": 2},
    "middle east eye":  {"name": "Middle East Eye",  "category": "independent",  "country": "UK",            "alignment": "independent", "tier": 2},
    "press tv":         {"name": "Press TV",         "category": "state_media",  "country": "Iran",          "alignment": "iran",        "tier": 3},
    "tehran times":     {"name": "Tehran Times",     "category": "state_media",  "country": "Iran",          "alignment": "iran",        "tier": 3},
    "wikipedia":        {"name": "Wikipedia",        "category": "encyclopedia", "country": "International", "alignment": "neutral",     "tier": 3},
    "wikinews":         {"name": "Wikinews",         "category": "encyclopedia", "country": "International", "alignment": "neutral",     "tier": 3},
    "reuters":          {"name": "Reuters",          "category": "wire_service", "country": "International", "alignment": "western",     "tier": 1},
    "ap news":          {"name": "AP News",          "category": "wire_service", "country": "International", "alignment": "western",     "tier": 1},
    "associated press": {"name": "AP News",          "category": "wire_service", "country": "International", "alignment": "western",     "tier": 1},
    "bbc":              {"name": "BBC",              "category": "western_msm",  "country": "UK",            "alignment": "western",     "tier": 1},
    "the guardian":     {"name": "The Guardian",     "category": "western_msm",  "country": "UK",            "alignment": "western",     "tier": 1},
    "new york times":   {"name": "New York Times",   "category": "western_msm",  "country": "USA",           "alignment": "western",     "tier": 1},
    "france 24":        {"name": "France 24",        "category": "western_msm",  "country": "France",        "alignment": "western",     "tier": 2},
    "deutsche welle":   {"name": "Deutsche Welle",   "category": "western_msm",  "country": "Germany",       "alignment": "western",     "tier": 2},
    "dw":               {"name": "Deutsche Welle",   "category": "western_msm",  "country": "Germany",       "alignment": "western",     "tier": 2},
    "al arabiya":       {"name": "Al Arabiya",       "category": "gulf_media",   "country": "Saudi Arabia",  "alignment": "gulf",        "tier": 2},
    "bellingcat":       {"name": "Bellingcat",       "category": "osint",        "country": "International", "alignment": "independent", "tier": 1},
    "nikkei asia":      {"name": "Nikkei Asia",      "category": "business",     "country": "Japan",         "alignment": "independent","tier": 1},
    "the japan times":  {"name": "The Japan Times",  "category": "regional_media","country": "Japan",        "alignment": "independent","tier": 2},
    "kyodo news":       {"name": "Kyodo News",       "category": "wire_service", "country": "Japan",         "alignment": "neutral",    "tier": 1},
    "yonhap":           {"name": "Yonhap News Agency","category": "wire_service", "country": "South Korea",   "alignment": "neutral",    "tier": 2},
    "cna":              {"name": "CNA",              "category": "regional_media","country": "Singapore",    "alignment": "neutral",    "tier": 2},
    "scmp":             {"name": "South China Morning Post","category": "regional_media","country": "Hong Kong","alignment": "independent","tier": 2},
    "the hindu":        {"name": "The Hindu",        "category": "regional_media","country": "India",        "alignment": "south_asian", "tier": 2},
    "the express tribune":{"name": "The Express Tribune","category": "regional_media","country": "Pakistan", "alignment": "south_asian", "tier": 2},
    "the print":        {"name": "The Print",        "category": "regional_media","country": "India",        "alignment": "south_asian", "tier": 2},
    "hindustan times":  {"name": "Hindustan Times",  "category": "regional_media","country": "India",        "alignment": "south_asian", "tier": 2},
    "the daily star":   {"name": "The Daily Star",   "category": "regional_media","country": "Bangladesh",   "alignment": "south_asian", "tier": 2},
    "republic world":   {"name": "Republic World",   "category": "regional_media","country": "India",        "alignment": "south_asian", "tier": 3},
    "ndtv":             {"name": "NDTV",             "category": "regional_media","country": "India",        "alignment": "south_asian", "tier": 2},
    "the jakarta post": {"name": "The Jakarta Post", "category": "regional_media","country": "Indonesia",    "alignment": "independent","tier": 2},
    "bangkok post":     {"name": "Bangkok Post",     "category": "regional_media","country": "Thailand",     "alignment": "independent","tier": 2},
    "rappler":          {"name": "Rappler",          "category": "regional_media","country": "Philippines",  "alignment": "independent","tier": 2},
    "inquirer":         {"name": "Philippine Daily Inquirer","category": "regional_media","country": "Philippines","alignment": "independent","tier": 2},
    "vietnamnet":       {"name": "VietnamNet",       "category": "state_media",  "country": "Vietnam",       "alignment": "eastern",    "tier": 2},
    "al-monitor":       {"name": "Al-Monitor",       "category": "regional_media","country": "International","alignment": "independent","tier": 2},
    "the national":     {"name": "The National",     "category": "gulf_media",   "country": "UAE",           "alignment": "gulf",       "tier": 2},
    "iran international":{"name": "Iran International","category": "independent", "country": "UK",           "alignment": "independent","tier": 3},
    "the moscow times": {"name": "The Moscow Times", "category": "independent",  "country": "Netherlands",   "alignment": "independent","tier": 2},
    "meduza":           {"name": "Meduza",           "category": "independent",  "country": "Latvia",        "alignment": "independent","tier": 1},
    "novaya gazeta":    {"name": "Novaya Gazeta Europe","category": "independent","country": "Latvia",       "alignment": "independent","tier": 1},
    "kyiv independent": {"name": "The Kyiv Independent","category": "independent","country": "Ukraine",      "alignment": "independent","tier": 2},
    "kyiv post":        {"name": "Kyiv Post",        "category": "independent",  "country": "Ukraine",       "alignment": "independent","tier": 2},
    "balkan insight":   {"name": "Balkan Insight",   "category": "independent",  "country": "International", "alignment": "independent","tier": 2},
    "daily maverick":   {"name": "Daily Maverick",   "category": "independent",  "country": "South Africa",  "alignment": "independent","tier": 2},
    "mail & guardian":  {"name": "Mail & Guardian",  "category": "independent",  "country": "South Africa",  "alignment": "independent","tier": 2},
    "premium times":    {"name": "Premium Times",    "category": "independent",  "country": "Nigeria",       "alignment": "independent","tier": 2},
    "the continent":    {"name": "The Continent",    "category": "independent",  "country": "South Africa",  "alignment": "independent","tier": 2},
    "allafrica":        {"name": "allAfrica.com",    "category": "wire_service", "country": "International", "alignment": "neutral",    "tier": 2},
    "africanews":       {"name": "AfricaNews",       "category": "regional_media","country": "France",       "alignment": "neutral",    "tier": 2},
    "mercopress":       {"name": "MercoPress",       "category": "independent",  "country": "Uruguay",       "alignment": "independent","tier": 2},
    "buenos aires times":{"name": "Buenos Aires Times","category": "independent","country": "Argentina",     "alignment": "independent","tier": 2},
    "folha de s.paulo": {"name": "Folha de S.Paulo", "category": "independent",  "country": "Brazil",        "alignment": "independent","tier": 2},
    "insight crime":    {"name": "InSight Crime",    "category": "osint",        "country": "International", "alignment": "independent","tier": 1},
    "telesur":          {"name": "teleSUR English",  "category": "state_media",  "country": "Venezuela",     "alignment": "eastern",    "tier": 3},
    "occrp":            {"name": "OCCRP",            "category": "osint",        "country": "International", "alignment": "independent","tier": 1},
    "opendemocracy":    {"name": "openDemocracy",    "category": "independent",  "country": "UK",            "alignment": "independent","tier": 2},
}

ALIGNMENT_GROUP_LABELS = {
    "western":     "Western Media",
    "eastern":     "Russian & Chinese State Media",
    "gulf":        "Gulf & Arab Media",
    "iran":        "Iranian State Media",
    "israel":      "Israeli Media",
    "south_asian": "South Asian Media",
    "independent": "Independent & Investigative Media",
    "neutral":     "Reference Sources",
}

from urllib.parse import urlparse

def get_source_metadata(url: str, publisher: str = "") -> dict:
    """
    Given a URL, return source metadata from the registry.
    Falls back to inferred metadata if domain is not in the registry.
    """
    domain = urlparse(url).netloc
    
    # Strip common feed subdomains
    for prefix in ["www.", "feeds.", "rss.", "news."]:
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
            
    if domain in SOURCE_REGISTRY:
        return SOURCE_REGISTRY[domain]
    for known_domain, meta in SOURCE_REGISTRY.items():
        if domain == known_domain or domain.endswith("." + known_domain):
            return meta

    # Infer from TLD or domain keywords
    inferred = {"name": domain, "category": "unknown", "country": "Unknown", "alignment": "unknown", "tier": 3}
    if any(x in domain for x in [".gov", ".mil"]):
        inferred["category"] = "official"
        inferred["alignment"] = "official"
        inferred["tier"] = 1
    elif domain.endswith(".ir"):
        inferred["alignment"] = "iran"
    elif domain.endswith(".il"):
        inferred["alignment"] = "israel"
    elif domain.endswith(".ru"):
        inferred["alignment"] = "eastern"
    elif domain.endswith(".cn"):
        inferred["alignment"] = "eastern"

    # Try publisher name fallback
    if publisher:
        pub_lower = publisher.strip().lower()
        if pub_lower in PUBLISHER_NAME_MAP:
            return PUBLISHER_NAME_MAP[pub_lower]
        pub_tokens = set(pub_lower.split())
        for known_name, meta in PUBLISHER_NAME_MAP.items():
            known_tokens = set(known_name.split())
            if pub_tokens == known_tokens:
                return meta

    return inferred
