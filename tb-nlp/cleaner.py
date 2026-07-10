import re
import unicodedata


class TextCleaner:
    """Text normalization engine tailored for financial news articles.

    Strips extraneous HTML and boilerplate while preserving financial figures,
    percentages, currency symbols, and corporate identifiers.
    """

    def clean(self, text: str) -> str:
        """Clean and normalize financial article text.

        Args:
            text (str): Raw article body text.

        Returns:
            str: Cleaned and normalized text.
        """
        if not text:
            return ""

        # 1. Strip residual HTML tags if any
        cleaned = re.sub(r"<[^>]*>", " ", text)

        # 2. Normalize Unicode characters (e.g. smart quotes, non-breaking spaces)
        cleaned = unicodedata.normalize("NFKC", cleaned)

        # Standardize common financial currency symbols and quotes
        cleaned = cleaned.replace("Rs.", "Rs ").replace("INR", "Rs ")
        cleaned = re.sub(r"[\u201c\u201d\u201e\u201f\u2033\u2036]", '"', cleaned)
        cleaned = re.sub(r"[\u2018\u2019\u201a\u201b\u2039\u203a]", "'", cleaned)

        # 3. Standardize whitespace while keeping paragraph structure intact
        lines = cleaned.splitlines()
        cleaned_lines = []
        for line in lines:
            line_str = " ".join(line.split())
            if line_str:
                cleaned_lines.append(line_str)

        cleaned_text = "\n".join(cleaned_lines)

        # 4. Remove unwanted website artifacts/disclaimers
        cleaned_text = re.sub(r"Follow us on (Telegram|Twitter|Facebook|LinkedIn|WhatsApp).*", "", cleaned_text, flags=re.I)
        cleaned_text = re.sub(r"Click here to read full story.*", "", cleaned_text, flags=re.I)

        return cleaned_text.strip()
