"""
python -m stock_news_analysis.analysis.sentiment_analysis
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from nltk.sentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import numpy as np
import torch.nn.functional as F
import os

# 🔑 You can add more strong keywords as you discover
# strong_positive_keywords = [
#     "acquisition", "record profit", "strong earnings", "merger", "order win",
#     "new contracts", "joint venture", "buyback", "dividend", "strategic partnership",
#     "record sales", "bonus issue", "approval received", "patent granted", "debt free",
#     "major contract", "foreign investment", "renewable push", "profit surge"
# ]

strong_positive_keywords = [
    "acquisition", "record profit", "strong earnings", "merger", "order win",
    "new contracts", "joint venture", "buyback", "dividend", "strategic partnership",
    "record sales", "bonus issue", "approval received", "patent granted", "debt free",
    "major contract", "foreign investment", "renewable push", "profit surge",
    "capacity expansion", "price hike", "board approval", "guidance raised",
    "beating estimates", "margin improvement", "robust demand", "record high",
    "order book strong", "cost synergies", "new facility", "expansion project",
    "regulatory nod", "signed MoU", "entered into agreement", "rollout plans",
    "market share gain", "capex infusion", "upgraded rating", "supply secured"
]

# Load VADER
vader_analyzer = SentimentIntensityAnalyzer()

# Load BERTweet
bertweet_model_name = "cardiffnlp/twitter-roberta-base-sentiment"
try:
    bertweet_tokenizer = AutoTokenizer.from_pretrained(bertweet_model_name)
    bertweet_model = AutoModelForSequenceClassification.from_pretrained(bertweet_model_name)
except Exception as e:
    print(f"[ERROR] Failed to load BERTweet model: {e}")
    bertweet_tokenizer, bertweet_model = None, None

# Load FinBERT
finbert_model_name = "yiyanghkust/finbert-tone"
try:
    finbert_tokenizer = AutoTokenizer.from_pretrained(finbert_model_name)
    finbert_model = AutoModelForSequenceClassification.from_pretrained(finbert_model_name)
except Exception as e:
    print(f"[ERROR] Failed to load FinBERT model: {e}")
    finbert_tokenizer, finbert_model = None, None

labels_finbert = ['negative', 'neutral', 'positive']
labels_bertweet = ['NEG', 'NEU', 'POS']

class EnhancedSentimentAnalyzer:
    def __init__(self):
        self.vader = vader_analyzer
        self.bertweet_model = bertweet_model
        self.bertweet_tokenizer = bertweet_tokenizer
        self.finbert_model = finbert_model
        self.finbert_tokenizer = finbert_tokenizer

    def analyze(self, text):
        if not isinstance(text, str) or not text.strip():
            return {"combined": 0, "confidence": 0}, "Neutral"

        text_lower = text.lower()

        # VADER
        vader_score = self.vader.polarity_scores(text)['compound']

        # TextBlob
        textblob_score = TextBlob(text).sentiment.polarity

        # BERTweet Transformer
        transformer_score = 0
        if self.bertweet_model and self.bertweet_tokenizer:
            inputs = self.bertweet_tokenizer(text, return_tensors="pt", truncation=True, padding='max_length', max_length=512)
            with torch.no_grad():
                outputs = self.bertweet_model(**inputs)
            probs = F.softmax(outputs.logits, dim=1)[0].numpy()
            transformer_score = float(probs[2] - probs[0])  # POS - NEG

        # FinBERT Transformer
        finbert_score = 0
        if self.finbert_model and self.finbert_tokenizer:
            inputs = self.finbert_tokenizer(text, return_tensors="pt", truncation=True, padding='max_length', max_length=512)
            with torch.no_grad():
                outputs = self.finbert_model(**inputs)
            probs = F.softmax(outputs.logits, dim=1)[0].numpy()
            finbert_score = float(probs[2] - probs[0])  # positive - negative

        # Combine all scores (weights can be adjusted)
        combined_score = (
            vader_score * 0.25 +
            textblob_score * 0.2 +
            transformer_score * 0.25 +
            finbert_score * 0.3
        )

        # Keyword boost
        if any(k in text_lower for k in strong_positive_keywords):
            combined_score += 0.2  # boost score

        # Clip to [-1, 1]
        combined_score = max(-1, min(1, combined_score))

        # Confidence
        confidence = abs(combined_score)

        # Final Sentiment Category
        if combined_score >= 0.75:
            sentiment = "Very Positive"
        elif combined_score >= 0.2:
            sentiment = "Positive"
        elif combined_score <= -0.75:
            sentiment = "Very Negative"
        elif combined_score <= -0.2:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"

        return {
            "vader": vader_score,
            "textblob": textblob_score,
            "transformer": transformer_score,
            "finbert": finbert_score,
            "combined": combined_score,
            "confidence": confidence
        }, sentiment


# Singleton instance
analyzer = EnhancedSentimentAnalyzer()

def analyze_sentiment(text):
    return analyzer.analyze(text)


# ✅ Sample Test Run
if __name__ == "__main__":
    test_text = """Tata Power has secured a ₹400 crore solar project from the Ministry of Defence, pushing its clean energy portfolio."""
    result = analyze_sentiment(test_text)
    vader_score = result[0]['vader']
    textblob_score = result[0]['textblob']
    bert_sentiment = result[0]['transformer']
    finbert_score = result[0]['finbert']
    confidence = result[0]['confidence']
    final_sentiment = result[1]
    print(vader_score, textblob_score, bert_sentiment, finbert_score, confidence, final_sentiment)
