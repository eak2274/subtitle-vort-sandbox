import re

class SimplePunctuator:
    """
    Простейшая пунктуация для субтитров:
    - добавляет точку в конце
    - добавляет запятые перед союзами
    - делает первую букву заглавной
    - ставит '?' если фраза начинается с вопросительного слова
    """

    question_words = {"кто", "что", "когда", "где", "почему", "зачем", "как"}

    def punctuate(self, text: str) -> str:
        text = text.strip()

        if not text:
            return text

        # Запятая перед "и", "но", "а"
        text = re.sub(r"\s+(и|но|а)\s+", r", \1 ", text)

        # Вопросительные предложения
        first = text.split()[0].lower()
        is_question = first in self.question_words

        # Заглавная буква
        text = text[0].upper() + text[1:]

        # Добавляем финальный знак
        if text[-1] not in ".?!":
            text += "?" if is_question else "."

        return text
