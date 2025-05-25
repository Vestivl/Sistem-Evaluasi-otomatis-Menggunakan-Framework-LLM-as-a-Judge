import json
import requests
import time
import os

# Masukkan API Key dari OpenRouter.ai
API_KEY = "API KEY ANDA"

MODEL_DEEPSEEK = "deepseek/deepseek-r1:free"
MODEL_JUDGE = "meta-llama/llama-4-maverick"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "HTTP-Referer": "https://chat.openai.com",
    "X-Title": "TA Evaluator"
}

def ask_openrouter(model, messages, max_tokens=1000):
    url = "https://openrouter.ai/api/v1/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens
    }
    response = requests.post(url, headers=headers, json=body)
    result = response.json()

    if "choices" in result:
        return result["choices"][0]["message"]["content"].strip()
    else:
        print(f"[❌] Gagal dengan model {model}:")
        print(result)
        return "ERROR"

def get_answer_from_model(question_item):
    q_text = question_item["question"]
    opts = "\n".join(question_item["options"])
    prompt = f"""
Berikut adalah soal pilihan ganda:

{q_text}

Pilihan:
{opts}

Berikan jawaban yang paling tepat (hanya huruf A, B, C, atau D).
"""
    messages = [{"role": "user", "content": prompt}]
    return ask_openrouter(MODEL_DEEPSEEK, messages)

def evaluate_answer(question_item, model_answer):
    q_text = question_item["question"]
    opts = "\n".join(question_item["options"])
    correct = question_item["correct_answer"]

    prompt = f"""
Soal: {q_text}
Pilihan:
{opts}

Jawaban model: {model_answer}
Jawaban benar: {correct}

Apakah jawaban model benar? Jelaskan secara singkat. Balas hanya:
- Benar/Salah
- Penjelasan 1-2 kalimat
"""
    messages = [{"role": "user", "content": prompt}]
    return ask_openrouter(MODEL_JUDGE, messages)

def load_existing_results(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

def save_results(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def show_statistics(results):
    total = 0
    benar = 0
    gagal = 0

    for item in results:
        evaluation = item.get("evaluation", "")
        if evaluation == "ERROR":
            gagal += 1
            continue
        if "Benar" in evaluation:
            benar += 1
        total += 1

    print("\n📊 Statistik Evaluasi:")
    print(f"📚 Total soal dievaluasi: {total}")
    print(f"✅ Jawaban benar: {benar}")
    print(f"❌ Jawaban salah: {total - benar}")
    print(f"⚠️ Soal gagal dievaluasi: {gagal}")

    if total > 0:
        akurasi = (benar / total) * 100
        print(f"🎯 Akurasi: {akurasi:.2f}%")
    else:
        print("⚠️ Tidak ada soal yang berhasil dievaluasi.")

def main():
    with open("soal.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    result_file = "results.json"
    existing_results = load_existing_results(result_file)
    existing_questions = {item["question"]: item for item in existing_results}

    for idx, item in enumerate(questions, 1):
        if item["question"] in existing_questions:
            print(f"[{idx}] ❎ Lewatkan, sudah ada: {item['question']}")
            continue

        print(f"[{idx}] ▶ Memproses soal baru: {item['question']}")
        model_answer = get_answer_from_model(item)
        print(f"Jawaban model: {model_answer}")
        item["model_answer"] = model_answer

        if model_answer == "ERROR":
            print("❌ Gagal menjawab soal.\n")
            item["evaluation"] = "ERROR"
            existing_results.append(item)
            continue

        evaluation = evaluate_answer(item, model_answer)
        print(f"Hasil evaluasi: {evaluation}")
        item["evaluation"] = evaluation
        print("-----\n")
        existing_results.append(item)
        time.sleep(1)

    save_results(result_file, existing_results)
    print(f"\n✅ Selesai. Hasil disimpan di {result_file}")
    show_statistics(existing_results)

if __name__ == "__main__":
    main()
