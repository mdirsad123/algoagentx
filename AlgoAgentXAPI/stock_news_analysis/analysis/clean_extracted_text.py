"""
python -m stock_news_analysis.analysis.clean_extracted_text
"""

import re

def advanced_clean_extracted_text(text: str) -> str:
    text = text.lower()

    # Remove emails and URLs
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)

    # Remove dates like 12-05-2024 or 12/05/2024
    text = re.sub(r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b', '', text)

    # Remove numbers attached to text like "25th"
    text = re.sub(r'\b\d+[a-z]+\b', '', text)

    # Remove non-essential punctuation (but keep % and .)
    text = re.sub(r'[^\w\s%.]', '', text)

    # Normalize whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

if __name__ == "__main__":
    result = advanced_clean_extracted_text("""The Board of Directors in their 267th Meeting held on 19th May 2025, resolved as follows. Approved the Audited Financial Statements and Audited financial Results for the Quarter and Financial Year ended 31st March 2025 and to publish the same.Recommended an Equity Dividend of Rs 0.50 per Equity Share of Rs 10 each. SIDDHARTH METALS LTD. iates for pharmaceuticals and Active Pharmaceutical Ingredients. Revenue from operations: 2,486.78 euros. Other Income: 23.66 euros. Expenses: 1,350.62 euros. Profit/(Los"J from Operations before. and after tax): 2,510.45 euros. RiQht: Share Capital1,018.25.25,25,1.018,25,.25,01,018,01,.01,017,017.00,01.01,016.00. Non-CURRENT ASSETS: Property, Plant and Equipment 4,102.96.96,4,334.94.94, 4,103.96., 4,000,000. Total Assets: 5,523.5,523,937,10,3.3. liabilities: 1,433.61.1,797.44. Alkali Metals Limited has a total of 9,293.63 million shares. The company has a net debt of 1,768.77 million pounds. The Company has a long-term debt of 3,434.23 million pounds and an equity of 4,452.48 million pounds as at March 31, 2025. The Board had recommended an Equity Dividend of Rs 0.50 per share of Rs 10 paid up. The Audited financial results of the Company have been prepared in accordance with Indain Accounting Standards. The Company is predominantly engaged in the Manufacture and Sale of Chemicals. Report on the audit of the Financial Results of ALKALI METALS LIMITED. Company has identified Geographical Segments based on location of customers as reportable segments. We conducted our audit in accordance with the Standards on Auditing (SAs) specified under section 143(10) of the Companies Act, 2013. We are independent of the Company inaccordance with the Code ofEthics issued by the Institute of Chartered Accountants of India. We believe that the audit evidence we have acquired is sufficient and appropriate to provide a basis for our opinion. Auditors' Responsibilities lor the Audit of the ~'inancial Results for the quarter and year ended March 31, 2025. Board of Directors are also responsible for overseeing the Company's financialreporting process. Fraud may involve collusion, forgery, purposefully omissions, misrepresentations, or the override of internal control. erial misstatement resulting from fraud is higher than for one resulting from error. Alkali Metals Limited is an Indian metals and mining company based in Hyderabad, India. The company is a member of the National Stock Exchange of India and the Bombay Stock Exchange. B. Venkatesh Babu, is in Practice since 2002. He is a reputed professional with extensive experience. His expertise includes conducting Secretarial Audits, IPOs and Compliance Audits. For period of 1 year from 1st April 2025 to  31st March 2026. Chartered Accountants (FRN: 005492S) have a rich experience in Audit, Taxation, Due Diligence and other related matters.""")
    print(result)