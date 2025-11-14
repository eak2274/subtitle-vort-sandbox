import json
import wave
import subprocess
import soundfile as sf
from vosk import Model, KaldiRecognizer
import srt
from datetime import timedelta
import noisereduce as nr
from simple_punct import SimplePunctuator
import argparse

AUDIO_TMP = "tmp_audio.wav"


def extract_audio(input_file):
    # 16 kHz, mono — оптимально для Vosk
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-ac", "1", "-ar", "16000",
        AUDIO_TMP
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def clean_audio():
    y, sr = sf.read(AUDIO_TMP)
    reduced = nr.reduce_noise(y=y, sr=sr)
    sf.write(AUDIO_TMP, reduced, sr)


def recognize_audio(model_path="models/vosk-model-ru-0.42"):
    wf = wave.open(AUDIO_TMP, "rb")
    model = Model(model_path)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    results = []
    while True:
        data = wf.readframes(8000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            results.append(json.loads(rec.Result()))
    results.append(json.loads(rec.FinalResult()))
    wf.close()
    return results


# ---------------------------------------
# ⭐ НОВОЕ: Разделение субтитров по паузам
# ---------------------------------------

def assemble_by_pause(results, PAUSE_THRESHOLD=0.55, MAX_LEN=12):
    """
    Разделяет фразы по паузам между словами.
    Параметры:
        PAUSE_THRESHOLD — минимальная пауза между словами (сек), чтобы начать новый субтитр
        MAX_LEN — максимальное число слов в одной фразе (для удобства чтения)
    """

    subs = []
    current = []

    last_end = None

    for chunk in results:
        if "result" not in chunk:
            continue

        for word in chunk["result"]:
            if last_end is not None:
                pause = word["start"] - last_end
                if pause >= PAUSE_THRESHOLD or len(current) >= MAX_LEN:
                    subs.append(current)
                    current = []
            current.append(word)
            last_end = word["end"]

    if current:
        subs.append(current)

    return subs


# ---------------------------------------
# Преобразование слов → SRT с пунктуацией
# ---------------------------------------

def words_to_srt_blocks(sub_list):
    punct = SimplePunctuator()

    subtitles = []
    counter = 1

    for words in sub_list:
        raw_text = " ".join([w["word"] for w in words])
        text = punct.punctuate(raw_text)  # добавляем пунктуацию

        start = timedelta(seconds=float(words[0]["start"]))
        end = timedelta(seconds=float(words[-1]["end"]))

        subtitles.append(srt.Subtitle(
            index=counter,
            start=start,
            end=end,
            content=text
        ))
        counter += 1

    return subtitles


# ---------------------------------------
# Основная функция
# ---------------------------------------

def film_to_srt(video_file, output_srt="output.srt"):
    print("🎬 Извлечение аудио…")
    extract_audio(video_file)

    print("🔊 Очистка и нормализация аудио…")
    clean_audio()

    print("🧠 Распознавание речи Vosk…")
    results = recognize_audio()

    print("📝 Сбор фраз по паузам…")
    sub_list = assemble_by_pause(results)

    print("🔧 Добавляем пунктуацию…")
    subtitles = words_to_srt_blocks(sub_list)

    print("💾 Сохранение SRT…")
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt.compose(subtitles))

    print("✔ Готово!")
    print(f"Файл сохранён: {output_srt}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Генерация субтитров из видео через Vosk"
    )

    parser.add_argument(
        "input",
        help="Путь к видеофайлу (MKV, AVI, MP4 и т.д.)"
    )

    parser.add_argument(
        "-o", "--output",
        default="output.srt",
        help="Путь к файлу субтитров (по умолчанию output.srt)"
    )

    args = parser.parse_args()

    film_to_srt(args.input, args.output)