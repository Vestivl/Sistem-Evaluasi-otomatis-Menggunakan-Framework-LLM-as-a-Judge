import json
import requests
import time

API_KEY = "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"  # Ganti dengan API Key kamu
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
    try:
        response = requests.post(url, headers=headers, json=body)
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"].strip()
        else:
            print(f"[❌] Gagal model {model}: {result}")
            return "ERROR"
    except Exception as e:
        print(f"[❌] Error API: {e}")
        return "ERROR"

def get_answer_from_model(question_item):
    q_text = question_item["question"]
    opts = "\n".join([f"{k}. {v}" for k, v in question_item["options"].items()])
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
    opts = "\n".join([f"{k}. {v}" for k, v in question_item["options"].items()])

    if "correct_answer" in question_item:
        correct = question_item["correct_answer"]
        prompt = f"""
Soal: {q_text}
Pilihan:
{opts}

Jawaban model: {model_answer}
Jawaban benar (kunci): {correct}

Apakah jawaban model benar? Jelaskan secara singkat. Balas hanya:
- Benar/Salah
- Penjelasan 1-2 kalimat
"""
        eval_type = "Training"
    else:
        prompt = f"""
Soal: {q_text}
Pilihan:
{opts}

Jawaban model: {model_answer}

Tidak tersedia jawaban benar (kunci).
Tolong nilai apakah jawaban model sudah tepat secara umum dan masuk akal.

Balas hanya:
- Benar/Salah
- Penjelasan 1-2 kalimat
"""
        eval_type = "Testing"

    messages = [{"role": "user", "content": prompt}]
    response = ask_openrouter(MODEL_JUDGE, messages)

    if response == "ERROR":
        return "ERROR"

    lines = response.strip().splitlines()
    label = "Tidak Jelas"
    reason = ""
    for line in lines:
        if "Benar" in line:
            label = "Benar"
        elif "Salah" in line:
            label = "Salah"
        else:
            reason += line.strip() + " "

    return {
        "label": label,
        "reason": reason.strip(),
        "type": eval_type
    }

def process_file(json_path, result_path):
    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    results = []
    for idx, item in enumerate(questions, 1):
        print(f"[{idx}] ▶ Memproses soal: {item['question']}")
        model_answer = get_answer_from_model(item)
        item["model_answer"] = model_answer

        if model_answer == "ERROR":
            item["evaluation"] = "ERROR"
            results.append(item)
            continue

        evaluation = evaluate_answer(item, model_answer)
        item["evaluation"] = evaluation
        results.append(item)
        time.sleep(1.5)

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results

def show_statistics(label, results):
    total = len(results)
    benar, salah, gagal = 0, 0, 0
    for item in results:
        eval_result = item.get("evaluation", {})
        if eval_result == "ERROR":
            gagal += 1
            continue
        label_eval = eval_result.get("label", "")
        if label_eval == "Benar":
            benar += 1
        elif label_eval == "Salah":
            salah += 1

    def akurasi(b, s):
        return (b / (b + s)) * 100 if (b + s) > 0 else 0

    print(f"\n📊 Statistik {label}:")
    print(f"- Benar: {benar}")
    print(f"- Salah: {salah}")
    print(f"- Gagal: {gagal}")
    print(f"- Akurasi: {akurasi(benar, salah):.2f}%")
    return benar, salah

def main():
    print("🔁 Memproses Training Set...")
    training_results = process_file("training.json", "training_results.json")
    benar_tr, salah_tr = show_statistics("Training", training_results)

    print("\n🔁 Memproses Testing Set...")
    testing_results = process_file("testing.json", "testing_results.json")
    benar_te, salah_te = show_statistics("Testing", testing_results)

    total_benar = benar_tr + benar_te
    total_salah = salah_tr + salah_te
    total_akurasi = (total_benar / (total_benar + total_salah)) * 100 if (total_benar + total_salah) > 0 else 0

    print(f"\n📌 Total Keseluruhan:")
    print(f"- Benar: {total_benar}")
    print(f"- Salah: {total_salah}")
    print(f"- Akurasi Total: {total_akurasi:.2f}%")

if __name__ == "__main__":
    main()
