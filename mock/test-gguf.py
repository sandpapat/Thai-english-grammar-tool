import os
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

# Set up paths
MODEL_DIR = "./models"
TRANS_REPO = "scb10x/typhoon-translate-4b-gguf"
TRANS_FILE = "typhoon-translate-4b-q4_k_m.gguf"
TRANS_PATH = f"{MODEL_DIR}/{TRANS_FILE}"

print("📥 Downloading GGUF model...")

# Download GGUF translator
if not os.path.exists(TRANS_PATH):
    print("⬇️ Downloading GGUF translator...")
    hf_hub_download(
        repo_id=TRANS_REPO,
        filename=TRANS_FILE,
        local_dir=MODEL_DIR,
        resume_download=True
    )
    print(f"✅ Translator saved to {TRANS_PATH}")
else:
    print(f"✅ GGUF translator already exists")

# Test loading the model with better parameters
print("🧠 Loading GGUF model...")
try:
    # Load with better parameters for CPU
    llm = Llama(
        model_path=TRANS_PATH,
        verbose=False,
        n_ctx=2048,  # Context length
        n_threads=4,  # Use 4 CPU threads
        n_batch=512   # Batch size
    )
    print("✅ GGUF model loaded successfully!")
    
    # Test translation with proper prompt format
    test_thai = "สวัสดีครับ"
    print(f"🧪 Testing translation: {test_thai}")
    
    # Better prompt format for Typhoon
    prompt = f"<s>Translate Thai to English: {test_thai}\nEnglish:"
    
    response = llm(
        prompt,
        max_tokens=50,
        temperature=0.1,  # Lower temperature for more consistent output
        stop=["</s>", "\n", "Thai:"],  # Stop tokens
        echo=False  # Don't echo the prompt
    )
    
    result = response['choices'][0]['text'].strip()
    print(f"📝 Result: {result}")
    
except Exception as e:
    print(f"❌ Error loading model: {e}")