#!/usr/bin/env python3
"""
Test script per verificare che il setup sia corretto
"""

import os
import sys
from pathlib import Path

def test_dependencies():
    """Test che tutte le dipendenze siano installate."""
    print("🔍 Testing dependencies...")
    
    # Test Python imports
    try:
        import openai
        print("✅ OpenAI library imported successfully")
    except ImportError as e:
        print(f"❌ OpenAI library import failed: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv library imported successfully")
    except ImportError as e:
        print(f"❌ python-dotenv library import failed: {e}")
        return False
    
    # Test .env file
    if os.path.exists('.env'):
        print("✅ .env file exists")
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key and api_key != 'your_openai_api_key_here':
            print("✅ OpenAI API key configured")
        else:
            print("⚠️  OpenAI API key not configured in .env file")
    else:
        print("❌ .env file not found")
        return False
    
    # Test ffmpeg
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ffmpeg is installed and working")
        else:
            print("❌ ffmpeg test failed")
            return False
    except FileNotFoundError:
        print("❌ ffmpeg not found in PATH")
        return False
    
    # Test directories
    for dir_name in ['temp', 'output']:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"ℹ️  Creating {dir_name}/ directory...")
            os.makedirs(dir_name, exist_ok=True)
    
    return True

def test_main_script():
    """Test che lo script principale funzioni."""
    print("\n🔍 Testing main script...")
    
    try:
        # Import main script
        sys.path.insert(0, '.')
        import main
        print("✅ main.py imports successfully")
        
        # Test help command
        import subprocess
        result = subprocess.run([sys.executable, 'main.py', '--help'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ main.py --help works correctly")
        else:
            print(f"❌ main.py --help failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing main script: {e}")
        return False
    
    return True

def main():
    """Main test function."""
    print("🧪 Recording to Tasks - Setup Test")
    print("=" * 40)
    
    success = True
    
    # Test dependencies
    if not test_dependencies():
        success = False
    
    # Test main script
    if not test_main_script():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 All tests passed! Setup is working correctly.")
        print("\n📋 Next steps:")
        print("1. Make sure your .env file has the correct OpenAI API key")
        print("2. Try processing a sample file: python main.py sample.mp4")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 