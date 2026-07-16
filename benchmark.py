import time
import json
import requests
import sys

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ollama_url = "http://localhost:11434"
    
    # Test data
    article_title = "ITC Q1 Results: Net profit rises 3% to ₹3,910 crore, beat estimates; FMCG revenue grows 6%"
    stocks_with_sentences = {
        "ITC": [
            "ITC Ltd on Thursday reported a 3.1% year-on-year rise in standalone net profit at ₹3,910.4 crore for the quarter ended June 30.",
            "Revenue from operations grew 6.1% to ₹16,989.6 crore, compared to ₹16,011.6 crore in the same period last year.",
            "The FMCG business segment recorded a revenue growth of 6.3% YoY to ₹5,025 crore."
        ],
        "Reliance": [
            "Reliance Industries shares traded marginally lower in sympathy with the broader market, though no direct announcements were made.",
            "Peer stock ITC gained ground after beating estimates, whereas Reliance remained flat."
        ]
    }
    
    # Format the prompt exactly like TargetSentimentAnalyzer._run_single_batch
    stock_blocks = []
    for stock, sents in stocks_with_sentences.items():
        stock_blocks.append(f"**{stock}**: {' '.join(sents[:3])}")
    combined_context = "\n".join(stock_blocks)
    stock_list = list(stocks_with_sentences.keys())

    prompt = (
        "You are a senior Indian equity research analyst.\n"
        f"Headline: {article_title}\n\n"
        "Relevant excerpts per stock:\n"
        f"{combined_context[:3000]}\n\n"
        f"Analyze the impact on EACH of these stocks: {', '.join(stock_list)}\n\n"
        "Respond ONLY in valid JSON as an array:\n"
        '[{"stock": "<name>", "sentiment": "Positive"|"Negative"|"Neutral", '
        '"confidence": <float 0.50-0.99>, '
        '"reason": "<2-3 sentences>"}]\n'
        "Include one entry per stock. No extra text."
    )
    
    models_to_test = [
        "llama3.2:1b",
        "qwen2.5:1.5b",
        "llama3.2:3b",
        "qwen2.5:3b",
        "gemma2:2b",
        "llama3.1:8b"
    ]
    
    results = []
    
    print("=" * 70)
    print("OLLAMA MODEL CPU BENCHMARK TOOL")
    print(f"URL: {ollama_url}")
    print(f"Target Stocks: {', '.join(stock_list)}")
    print("=" * 70)
    
    for model in models_to_test:
        print(f"\nTesting model: {model} ... ", end="", flush=True)
        
        # Check if model is pulled/available
        try:
            check_res = requests.post(f"{ollama_url}/api/show", json={"name": model}, timeout=5)
            if check_res.status_code != 200:
                print("SKIPPED (Model not pulled/installed in Ollama)")
                results.append({
                    "model": model,
                    "status": "Skipped",
                    "time": "-",
                    "json_valid": "-",
                    "output": "Not pulled"
                })
                continue
        except Exception:
            print("ERROR (Ollama server not reachable)")
            print("\nPlease make sure Ollama is running (`ollama serve`) on localhost:11434.")
            return

        start_time = time.time()
        try:
            res = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=1800 # Allow up to 30 mins for 8b
            )
            
            elapsed = time.time() - start_time
            
            if res.status_code == 200:
                response_text = res.json().get("response", "").strip()
                
                # Verify JSON format
                is_valid_json = False
                try:
                    parsed = json.loads(response_text)
                    if isinstance(parsed, dict) and "stock" in parsed:
                        parsed = [parsed]
                        
                    if isinstance(parsed, list) and len(parsed) > 0:
                        # Check first item structure
                        item = parsed[0]
                        if "stock" in item and "sentiment" in item and "confidence" in item:
                            is_valid_json = True
                    elif isinstance(parsed, dict):
                        # Some models wrap the array in a dict keys
                        for key in ("results", "stocks", "analysis"):
                            if key in parsed and isinstance(parsed[key], list):
                                is_valid_json = True
                                break
                except Exception:
                    pass
                
                status_str = "SUCCESS" if is_valid_json else "JSON FORMAT ERROR"
                print(f"Completed in {elapsed:.2f}s ({status_str})")
                
                results.append({
                    "model": model,
                    "status": "Success" if is_valid_json else "Format Error",
                    "time": f"{elapsed:.2f}s",
                    "json_valid": "Yes" if is_valid_json else "No",
                    "output": response_text[:120] + "..." if len(response_text) > 120 else response_text
                })
            else:
                print(f"FAILED (HTTP Status {res.status_code})")
                results.append({
                    "model": model,
                    "status": f"HTTP {res.status_code}",
                    "time": "-",
                    "json_valid": "-",
                    "output": ""
                })
                
        except requests.exceptions.Timeout:
            print("TIMED OUT")
            results.append({
                "model": model,
                "status": "Timeout",
                "time": ">30m",
                "json_valid": "-",
                "output": ""
            })
        except Exception as e:
            print(f"ERROR ({str(e)})")
            results.append({
                "model": model,
                "status": "Error",
                "time": "-",
                "json_valid": "-",
                "output": str(e)
            })

    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"{'Model Name':<20} | {'Status':<12} | {'Time (s)':<10} | {'JSON Valid':<10}")
    print("-" * 70)
    for r in results:
        print(f"{r['model']:<20} | {r['status']:<12} | {r['time']:<10} | {r['json_valid']:<10}")
    print("=" * 70)
    print("\nSample Outputs:")
    for r in results:
        if r['status'] in ("Success", "Format Error"):
            print(f"\n--- {r['model']} output snippet ---")
            print(r['output'])

if __name__ == "__main__":
    main()
