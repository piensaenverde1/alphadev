"""
Advanced NLP sentiment analysis for financial text.

Attempts to use FinBERT (ProsusAI/finbert) via HuggingFace transformers
for state-of-the-art financial sentiment. Falls back to an enhanced
weighted lexicon when transformers is not installed or the model cannot
be loaded.
"""

import re
import os
from typing import Dict, List, Optional, Tuple

# Optional heavy dependency – imported lazily so the module always loads.
try:
    from transformers import pipeline as _hf_pipeline  # type: ignore
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Lexicon
# ---------------------------------------------------------------------------

POSITIVE_TERMS: Dict[str, float] = {
    # Earnings / performance
    "beat": 0.80, "beats": 0.80, "exceeded": 0.75, "outperform": 0.75,
    "outperformed": 0.75, "surpassed": 0.72, "record": 0.70,
    "record-high": 0.78, "record high": 0.78, "all-time high": 0.80,
    "breakout": 0.65, "profitable": 0.65, "profit": 0.60,
    "revenue growth": 0.72, "strong earnings": 0.80, "earnings beat": 0.85,
    "guidance raised": 0.82, "raised guidance": 0.82, "upgrade": 0.68,
    "upgraded": 0.68, "buy rating": 0.72, "overweight": 0.65,
    # Market / price action
    "rally": 0.65, "rallied": 0.65, "surge": 0.70, "surged": 0.70,
    "soar": 0.72, "soared": 0.72, "spike": 0.60, "gain": 0.55,
    "gains": 0.55, "advance": 0.55, "advances": 0.55, "climb": 0.55,
    "climbed": 0.55, "jump": 0.60, "jumped": 0.60, "boom": 0.70,
    "booming": 0.70, "bullish": 0.70, "bull market": 0.72,
    "momentum": 0.55, "rebound": 0.60, "recovery": 0.60,
    # Corporate actions
    "acquisition": 0.50, "merger": 0.50, "buyback": 0.65,
    "share repurchase": 0.65, "dividend increase": 0.70,
    "dividend raised": 0.70, "ipo": 0.55, "spin-off": 0.50,
    # Financial health
    "debt-free": 0.75, "cash flow positive": 0.72, "margin expansion": 0.68,
    "cost reduction": 0.60, "efficiency": 0.50, "innovation": 0.55,
    "growth": 0.55, "expansion": 0.58, "market share": 0.52,
    "dominant": 0.60, "leadership": 0.55, "competitive advantage": 0.65,
    # Macro / general positive
    "rate cut": 0.65, "stimulus": 0.60, "quantitative easing": 0.55,
    "soft landing": 0.60, "strong economy": 0.65, "low unemployment": 0.62,
    "consumer confidence": 0.58, "optimistic": 0.60, "positive outlook": 0.68,
    "upside": 0.60, "opportunity": 0.52, "undervalued": 0.62,
    "value": 0.45, "robust": 0.60, "solid": 0.55, "healthy": 0.55,
    "strong": 0.55, "impressive": 0.62, "exceptional": 0.70,
    "outstanding": 0.72, "excellent": 0.70, "best": 0.55,
}

NEGATIVE_TERMS: Dict[str, float] = {
    # Catastrophic events
    "bankrupt": -1.00, "bankruptcy": -1.00, "insolvent": -0.95,
    "default": -0.90, "fraud": -0.92, "scandal": -0.85,
    "crash": -0.90, "collapsed": -0.88, "collapse": -0.88,
    "crisis": -0.82, "catastrophe": -0.88, "disaster": -0.85,
    # Earnings / performance
    "miss": -0.75, "missed": -0.75, "disappointing": -0.72,
    "disappointed": -0.72, "below expectations": -0.75,
    "guidance cut": -0.82, "lowered guidance": -0.82, "downgrade": -0.70,
    "downgraded": -0.70, "sell rating": -0.72, "underweight": -0.65,
    "earnings miss": -0.82, "revenue decline": -0.72, "loss": -0.65,
    "net loss": -0.72, "operating loss": -0.72,
    # Market / price action
    "plunge": -0.82, "plunged": -0.82, "tumble": -0.75, "tumbled": -0.75,
    "slump": -0.70, "slumped": -0.70, "tank": -0.72, "tanked": -0.72,
    "drop": -0.60, "dropped": -0.60, "fall": -0.55, "fell": -0.55,
    "decline": -0.60, "declined": -0.60, "sell-off": -0.72,
    "selloff": -0.72, "bearish": -0.68, "bear market": -0.72,
    "correction": -0.55, "downturn": -0.65, "recession": -0.78,
    "depression": -0.85, "stagflation": -0.75, "inflation": -0.50,
    # Corporate / operational
    "layoff": -0.70, "layoffs": -0.70, "job cuts": -0.72,
    "restructuring": -0.55, "write-off": -0.68, "write-down": -0.68,
    "impairment": -0.65, "recall": -0.60, "investigation": -0.65,
    "lawsuit": -0.60, "litigation": -0.58, "fine": -0.60,
    "penalty": -0.60, "regulation": -0.45, "ban": -0.65,
    "delisted": -0.85, "delisting": -0.85,
    # Macro / general negative
    "rate hike": -0.55, "tightening": -0.50, "hawkish": -0.55,
    "overvalued": -0.58, "bubble": -0.65, "debt": -0.45,
    "deficit": -0.50, "weak": -0.55, "poor": -0.60, "disappoints": -0.70,
    "concern": -0.48, "risk": -0.40, "uncertainty": -0.45,
    "volatile": -0.42, "volatility": -0.42, "headwind": -0.55,
    "warning": -0.60, "caution": -0.50, "slowdown": -0.60,
    "contraction": -0.65, "negative outlook": -0.70,
}

# Intensity multipliers applied to preceding/modifying adverbs
INTENSITY_MODIFIERS: Dict[str, float] = {
    "massive": 1.50, "huge": 1.40, "major": 1.30, "significant": 1.25,
    "sharp": 1.30, "severe": 1.40, "extreme": 1.45, "dramatic": 1.35,
    "slight": 0.60, "small": 0.55, "minor": 0.50, "modest": 0.65,
    "slightly": 0.60, "marginally": 0.50,
    "substantially": 1.30, "considerably": 1.25, "significantly": 1.25,
    "greatly": 1.30, "strongly": 1.30, "weakly": 0.65,
}

# Negation words that flip the sign of a sentiment term
NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "cannot", "can't", "won't",
    "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "hardly",
    "barely", "scarcely", "without", "lack", "lacking", "fails", "failed",
}

# Regex patterns for financial events
_EVENT_PATTERNS: Dict[str, re.Pattern] = {
    "earnings_beat":   re.compile(r"\bearnings?\s+beat\b|\bbeat\s+(?:earnings?|estimates?|expectations?)\b", re.I),
    "earnings_miss":   re.compile(r"\bearnings?\s+miss\b|\bmissed?\s+(?:earnings?|estimates?|expectations?)\b", re.I),
    "rate_hike":       re.compile(r"\brate\s+hike\b|\braised?\s+(?:interest\s+)?rates?\b|\bhawkish\b", re.I),
    "rate_cut":        re.compile(r"\brate\s+cut\b|\blowered?\s+(?:interest\s+)?rates?\b|\bdovish\b", re.I),
    "layoffs":         re.compile(r"\blayoffs?\b|\bjob\s+cuts?\b|\breducing\s+headcount\b|\bworkforce\s+reduction\b", re.I),
    "merger":          re.compile(r"\bmerger\b|\bacquisition\b|\btakeover\b|\bmerging\b|\bacquires?\b", re.I),
    "ipo":             re.compile(r"\bIPO\b|\binitial\s+public\s+offering\b|\bgoing\s+public\b", re.I),
    "bankruptcy":      re.compile(r"\bbankruptcy\b|\bchapter\s+11\b|\bchapter\s+7\b|\binsolvent\b|\bdefault\b", re.I),
    "record_high":     re.compile(r"\brecord[\s-]high\b|\ball[\s-]time\s+high\b|\bnew\s+(?:52[\s-]week\s+)?high\b", re.I),
    "dividend":        re.compile(r"\bdividend\b|\bdistribution\b|\bpayout\b", re.I),
    "buyback":         re.compile(r"\bbuyback\b|\bshare\s+repurchase\b|\brepurchasing\s+shares\b", re.I),
    "guidance_raised": re.compile(r"\braised?\s+guidance\b|\bguidance\s+(?:raised?|increased?|lifted?)\b", re.I),
    "guidance_cut":    re.compile(r"\bcut\s+guidance\b|\bguidance\s+(?:cut|lowered?|reduced?)\b", re.I),
    "fraud":           re.compile(r"\bfraud\b|\baccounting\s+irregularit\w+\b|\bembezzl\w+\b|\bscandal\b", re.I),
    "upgrade":         re.compile(r"\bupgraded?\s+to\b|\banalyst\s+upgrade\b", re.I),
    "downgrade":       re.compile(r"\bdowngraded?\s+to\b|\banalyst\s+downgrade\b", re.I),
}

# Simple ticker pattern (1–5 uppercase letters, optionally preceded by $)
_TICKER_PATTERN = re.compile(r"(?<!\w)\$?([A-Z]{1,5})(?!\w)")

# Common company name suffixes to help identify company mentions
_COMPANY_SUFFIX = re.compile(
    r"\b([A-Z][A-Za-z0-9&\s\-'\.]{1,40}?\s*(?:Inc\.?|Corp\.?|Ltd\.?|LLC\.?|PLC\.?|SA\.?|AG\.?|NV\.?))",
    re.I,
)

# Numbers pattern (financial figures like "$1.2B", "3.5%", "EUR 100M")
_NUMBER_PATTERN = re.compile(
    r"(?:[\$€£¥]?\s*\d[\d,]*(?:\.\d+)?(?:\s*[BMKTbmkt](?:illion|rillion)?)?\s*(?:%|percent|bps|basis\s+points)?)"
)


class AdvancedSentiment:
    """
    Advanced financial sentiment analyser.

    Tries to load FinBERT on construction. If the model or the
    ``transformers`` library is unavailable, all analysis falls back to an
    enhanced weighted lexicon with negation and intensity handling.
    """

    def __init__(self) -> None:
        self._pipeline = None
        self._method: str = "lexicon"

        if _TRANSFORMERS_AVAILABLE:
            try:
                self._pipeline = _hf_pipeline(
                    "text-classification",
                    model="ProsusAI/finbert",
                    tokenizer="ProsusAI/finbert",
                    top_k=None,  # return all label scores
                    truncation=True,
                    max_length=512,
                )
                self._method = "finbert"
            except Exception:
                # Model download or CUDA errors – degrade gracefully
                self._pipeline = None
                self._method = "lexicon"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, text: str) -> Dict:
        """
        Analyse a single piece of financial text.

        Returns
        -------
        dict with keys:
            sentiment  – "POSITIVE", "NEGATIVE", or "NEUTRAL"
            score      – float in [-1.0, 1.0]
            confidence – float in [0.0, 1.0]
            method     – "finbert" or "lexicon"
        """
        if not text or not text.strip():
            return self._neutral_result()

        if self._pipeline is not None:
            return self._analyze_finbert(text)
        return self._analyze_lexicon(text)

    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        Efficiently analyse a list of texts.

        Uses FinBERT's native batching when available; otherwise processes
        each text through the lexicon (which is already fast).
        """
        if not texts:
            return []

        if self._pipeline is not None:
            return self._analyze_finbert_batch(texts)

        return [self._analyze_lexicon(t) for t in texts]

    def analyze_article(self, title: str, summary: str) -> Dict:
        """
        Combined sentiment analysis for a news article.

        The title is weighted more heavily (2x) than the body summary.
        Entity extraction is also performed and included in the result.
        """
        # Double the title to give it 2x weight relative to the summary
        combined_text = f"{title} {title} {summary}".strip()

        result = self.analyze(combined_text)
        entities = self.extract_financial_entities(combined_text)

        result["title"] = title
        result["summary_snippet"] = summary[:200] if summary else ""
        result["entities"] = entities

        # Adjust score slightly based on detected events
        event_adjustment = self._events_to_adjustment(entities.get("events", []))
        adjusted_score = max(-1.0, min(1.0, result["score"] + event_adjustment * 0.15))
        result["score"] = round(adjusted_score, 4)
        result["sentiment"] = self._score_to_label(result["score"])

        return result

    def extract_financial_entities(self, text: str) -> Dict:
        """
        Extract key financial entities from text.

        Returns a dict with:
            companies – list of company name strings
            tickers   – list of ticker symbols (filtered for common words)
            events    – list of event type strings
            numbers   – list of numeric/financial figure strings
        """
        if not text:
            return {"companies": [], "tickers": [], "events": [], "numbers": []}

        # Tickers: uppercase 1-5 char sequences, filter out common non-ticker caps
        raw_tickers = _TICKER_PATTERN.findall(text)
        stop_caps = {
            "A", "I", "AN", "AT", "BE", "BY", "DO", "GO", "IF", "IN",
            "IS", "IT", "MY", "NO", "OF", "ON", "OR", "SO", "TO", "UP",
            "US", "WE", "AS", "AM", "PM", "CEO", "CFO", "COO", "IPO",
            "ETF", "GDP", "CPI", "PPI", "FED", "SEC", "NYSE", "NASDAQ",
            "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
        }
        tickers = sorted({t for t in raw_tickers if t not in stop_caps})

        # Company names via suffix pattern
        company_matches = _COMPANY_SUFFIX.findall(text)
        companies = sorted({c.strip() for c in company_matches if len(c.strip()) > 3})

        # Financial events via regex
        events: List[str] = [
            event_name
            for event_name, pattern in _EVENT_PATTERNS.items()
            if pattern.search(text)
        ]

        # Numeric financial figures
        number_matches = _NUMBER_PATTERN.findall(text)
        numbers = [n.strip() for n in number_matches if n.strip()]

        return {
            "companies": companies[:10],
            "tickers": tickers[:10],
            "events": events,
            "numbers": numbers[:20],
        }

    def get_impact_score(
        self, article: Dict, portfolio_symbols: List[str]
    ) -> float:
        """
        Return an impact score in [-1.0, 1.0] for an article relative to
        a portfolio.

        The base score comes from sentiment analysis; it is amplified when
        the article mentions symbols that appear in *portfolio_symbols*.
        """
        title = article.get("title", "")
        summary = article.get("summary", article.get("description", ""))

        analysis = self.analyze_article(title, summary)
        base_score = analysis.get("score", 0.0)

        # Check how many portfolio symbols are mentioned
        entities = analysis.get("entities") or self.extract_financial_entities(
            f"{title} {summary}"
        )
        mentioned_tickers = {t.upper() for t in entities.get("tickers", [])}
        # Normalise portfolio symbols (strip exchange suffixes)
        portfolio_set = {
            s.upper().replace("/USDT", "").replace("/USD", "").replace("/EUR", "")
            for s in portfolio_symbols
        }

        overlap = mentioned_tickers & portfolio_set
        if overlap:
            # Small boost/penalty scaled by number of overlapping holdings
            relevance_boost = min(0.30, len(overlap) * 0.10)
            adjusted = base_score + (relevance_boost if base_score >= 0 else -relevance_boost)
        else:
            adjusted = base_score

        return round(max(-1.0, min(1.0, adjusted)), 4)

    # ------------------------------------------------------------------
    # FinBERT helpers
    # ------------------------------------------------------------------

    def _analyze_finbert(self, text: str) -> Dict:
        """Run a single text through the FinBERT pipeline."""
        try:
            raw = self._pipeline(text[:512])
            # pipeline returns list-of-lists when top_k=None
            scores_list = raw[0] if isinstance(raw[0], list) else raw
            label_map = {item["label"].lower(): item["score"] for item in scores_list}

            pos = label_map.get("positive", 0.0)
            neg = label_map.get("negative", 0.0)
            neu = label_map.get("neutral", 0.0)

            score = pos - neg  # range roughly [-1, 1]
            confidence = max(pos, neg, neu)

            return {
                "sentiment": self._score_to_label(score),
                "score": round(score, 4),
                "confidence": round(confidence, 4),
                "method": "finbert",
            }
        except Exception:
            return self._analyze_lexicon(text)

    def _analyze_finbert_batch(self, texts: List[str]) -> List[Dict]:
        """Batch analyse using FinBERT's native batching."""
        truncated = [t[:512] for t in texts]
        try:
            raw_batch = self._pipeline(truncated)
            results = []
            for raw in raw_batch:
                scores_list = raw if isinstance(raw, list) else [raw]
                label_map = {item["label"].lower(): item["score"] for item in scores_list}
                pos = label_map.get("positive", 0.0)
                neg = label_map.get("negative", 0.0)
                neu = label_map.get("neutral", 0.0)
                score = pos - neg
                results.append({
                    "sentiment": self._score_to_label(score),
                    "score": round(score, 4),
                    "confidence": round(max(pos, neg, neu), 4),
                    "method": "finbert",
                })
            return results
        except Exception:
            return [self._analyze_lexicon(t) for t in texts]

    # ------------------------------------------------------------------
    # Enhanced lexicon helpers
    # ------------------------------------------------------------------

    def _analyze_lexicon(self, text: str) -> Dict:
        """Score text using the weighted lexicon with negation + intensity."""
        tokens = re.findall(r"\b\w[\w'-]*\b", text.lower())
        if not tokens:
            return self._neutral_result()

        total_score = 0.0
        total_weight = 0.0

        for i, token in enumerate(tokens):
            # Window of up to 3 preceding tokens for context
            window = tokens[max(0, i - 3): i]

            # Try longest phrase match first (3-gram → 2-gram → 1-gram)
            matched = False
            for phrase_len in (3, 2, 1):
                start = i - phrase_len + 1
                if start < 0:
                    continue
                phrase = " ".join(tokens[start: i + 1])
                base = POSITIVE_TERMS.get(phrase) or NEGATIVE_TERMS.get(phrase)
                if base is not None:
                    adjusted = self._apply_context(base, window)
                    total_score += adjusted
                    total_weight += abs(adjusted)
                    matched = True
                    break

        if total_weight == 0.0:
            return self._neutral_result()

        # Weighted average compressed to [-1, 1]
        score = max(-1.0, min(1.0, total_score / max(total_weight, 1.0)))

        # Confidence: term density relative to text length
        term_density = total_weight / max(len(tokens), 1)
        confidence = min(1.0, term_density * 5.0)

        return {
            "sentiment": self._score_to_label(score),
            "score": round(score, 4),
            "confidence": round(confidence, 4),
            "method": "lexicon",
        }

    def _apply_context(self, base_score: float, window: List[str]) -> float:
        """Apply negation and intensity modifiers from preceding tokens."""
        score = base_score

        # Negation: flip sign if a negation word appears in the window
        if any(w in NEGATION_WORDS for w in window):
            score = -score

        # Intensity: use the strongest modifier found in the window
        multiplier = 1.0
        for w in window:
            m = INTENSITY_MODIFIERS.get(w, 1.0)
            if m > 1.0:
                multiplier = max(multiplier, m)
            elif m < 1.0:
                multiplier = min(multiplier, m)
        score *= multiplier

        return score

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_label(score: float) -> str:
        if score >= 0.05:
            return "POSITIVE"
        if score <= -0.05:
            return "NEGATIVE"
        return "NEUTRAL"

    @staticmethod
    def _neutral_result() -> Dict:
        return {
            "sentiment": "NEUTRAL",
            "score": 0.0,
            "confidence": 0.0,
            "method": "lexicon",
        }

    @staticmethod
    def _events_to_adjustment(events: List[str]) -> float:
        """Map a list of detected events to a net directional adjustment."""
        positive_events = {
            "earnings_beat", "rate_cut", "guidance_raised",
            "record_high", "buyback", "upgrade",
        }
        negative_events = {
            "earnings_miss", "rate_hike", "guidance_cut",
            "bankruptcy", "fraud", "layoffs", "downgrade",
        }
        net = (
            sum(1 for e in events if e in positive_events)
            - sum(1 for e in events if e in negative_events)
        )
        return float(max(-3, min(3, net)))
