"""
python -m stock_news_analysis.analysis.sentiment_FinBert
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F
import os

# Strong financial positive keywords (optional for additional boosts, you can adjust or remove)
strong_positive_keywords = [
    "acquisition", "record profit", "strong earnings", "merger", "order win",
    "new contracts", "joint venture", "buyback", "dividend", "strategic partnership"
]

# Load FinBERT model & tokenizer with error handling
model_name = "yiyanghkust/finbert-tone"
try:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
except Exception as e:
    print(f"[ERROR] Failed to load FinBERT model: {e}")
    tokenizer = None
    model = None

# FinBERT labels (specific to FinBERT)
labels = ['negative', 'neutral', 'positive']

class FinBERTSentimentAnalyzer:
    def __init__(self):
        self.model = model
        self.tokenizer = tokenizer
        self.labels = labels

    def analyze(self, text):
        if not isinstance(text, str) or not text.strip():
            return {"finbert": 0, "confidence": 0}, "Neutral"

        if self.model is None or self.tokenizer is None:
            return {"finbert": 0, "confidence": 0}, "Model Load Error"

        # Encode the text
        encoded_input = self.tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            padding='max_length',
            max_length=512
        )

        with torch.no_grad():
            output = self.model(**encoded_input)

        # Softmax to get probabilities
        probs = F.softmax(output.logits, dim=1)[0].numpy()
        prob_dict = {self.labels[i]: float(probs[i]) for i in range(len(self.labels))}

        # Determine highest probability label and confidence
        max_index = probs.argmax()
        sentiment_label = self.labels[max_index]
        confidence = float(probs[max_index])

        # Optional: boost if strong positive keywords are present
        text_lower = text.lower()
        for keyword in strong_positive_keywords:
            if keyword in text_lower and sentiment_label == "positive":
                confidence = min(confidence + 0.1, 1.0)  # small boost
                break

        return {
            "finbert": prob_dict.get("positive", 0) - prob_dict.get("negative", 0),
            "probabilities": prob_dict,
            "confidence": confidence
        }, sentiment_label.capitalize()

# Singleton instance
analyzer = FinBERTSentimentAnalyzer()

def analyze_sentiment_finbert(text):
    return analyzer.analyze(text)

# Test Run
if __name__ == "__main__":
    test_text = """FERTILIZERS AND CHEMICALS TRAVANCORE LIMITED has informed the Exchange regarding Outcome of Board Meeting held on 26-May-2025 for Dividend"""
    
    result = analyze_sentiment_finbert(test_text)
    finbert_score = result[0]['finbert']
    confidence = result[0]['confidence']
    final_sentiment = result[1]
    print("FinBERT Score (Positive-Negative):", finbert_score)
    print("Confidence:", confidence)
    print("Final Sentiment:", final_sentiment)
    print("Probabilities:", result[0]['probabilities'])
