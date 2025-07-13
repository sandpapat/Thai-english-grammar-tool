#!/usr/bin/env python3
"""
Setup script to download GGUF models for deployment
This script is optional and mainly for VM deployment setup
"""

import os
from huggingface_hub import hf_hub_download

# Configuration
MODEL_DIR = "./models"
TRANS_REPO = "scb10x/typhoon-translate-4b-gguf"
TRANS_FILE = "typhoon-translate-4b-q4_k_m.gguf"
TRANS_PATH = f"{MODEL_DIR}/{TRANS_FILE}"

def ensure_model_dir():
    """Create models directory if it doesn't exist"""
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        print(f"✅ Created directory: {MODEL_DIR}")

def download_typhoon_translate():
    """Download Typhoon Translate GGUF model"""
    if os.path.exists(TRANS_PATH):
        print(f"✅ Typhoon Translate model already exists at {TRANS_PATH}")
        return
    
    print("📥 Downloading Typhoon Translate 4B GGUF model...")
    print(f"   Repository: {TRANS_REPO}")
    print(f"   File: {TRANS_FILE}")
    print("   This may take a while (model size ~2.6GB)")
    
    try:
        hf_hub_download(
            repo_id=TRANS_REPO,
            filename=TRANS_FILE,
            local_dir=MODEL_DIR,
            resume_download=True
        )
        print(f"✅ Model downloaded successfully to {TRANS_PATH}")
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        print("   Please check your internet connection and try again")

def verify_setup():
    """Verify the model setup"""
    print("\n🔍 Verifying model setup...")
    
    if os.path.exists(TRANS_PATH):
        size_mb = os.path.getsize(TRANS_PATH) / (1024 * 1024)
        print(f"✅ Typhoon Translate model found ({size_mb:.1f} MB)")
    else:
        print("❌ Typhoon Translate model not found")
    
    # Test import
    try:
        import llama_cpp
        print("✅ llama-cpp-python is installed")
    except ImportError:
        print("❌ llama-cpp-python not installed")
        print("   Run: pip install llama-cpp-python==0.2.90")

def main():
    print("🚀 Typhoon GGUF Model Setup Script\n")
    
    # Ensure model directory exists
    ensure_model_dir()
    
    # Download model
    download_typhoon_translate()
    
    # Verify setup
    verify_setup()
    
    print("\n✨ Setup complete!")
    print("   You can now run the Flask application with GGUF model support")

if __name__ == "__main__":
    main()