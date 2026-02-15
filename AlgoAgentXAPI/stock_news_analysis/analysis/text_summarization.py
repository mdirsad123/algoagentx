"""
python -m stock_news_analysis.analysis.text_summarization
"""

from transformers import pipeline

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def summarize_text(text: str, max_chunk_chars: int = 2000) -> str:
    """
    Summarizes long text in chunks using a transformer model.

    Parameters:
        text (str): The full extracted text.
        max_chunk_chars (int): Max characters per chunk.

    Returns:
        str: Final combined summary.
    """
    chunks = [text[i:i+max_chunk_chars] for i in range(0, len(text), max_chunk_chars)]
    summaries = []

    for chunk in chunks:
        summary = summarizer(chunk, max_length=130, min_length=30, do_sample=False)
        summaries.append(summary[0]['summary_text'])

    return " ".join(summaries)

if __name__ == "__main__":
        text = ""
        summary = summarize_text(text)


