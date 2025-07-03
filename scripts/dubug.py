import requests
import mimetypes
from pathlib import Path

# Configuration
VIDEO_PATH = r"C:\Users\anand\Downloads\gum.mp4"
BASE_URL = "http://localhost:8000"

def debug_file_info():
    """Debug information about the video file"""
    
    print("🔍 File Debug Information")
    print("=" * 50)
    
    # Check if file exists
    file_path = Path(VIDEO_PATH)
    if not file_path.exists():
        print(f"❌ File not found: {VIDEO_PATH}")
        return
    
    # Basic file info
    print(f"📁 File: {file_path.name}")
    print(f"📊 Size: {file_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"🏷️  Extension: {file_path.suffix}")
    
    # MIME type detection
    mime_type, encoding = mimetypes.guess_type(str(file_path))
    print(f"🎭 Detected MIME type: {mime_type}")
    print(f"📝 Encoding: {encoding}")
    
    # Test what gets sent in the request
    print(f"\n📤 Testing upload request...")
    
    try:
        with open(VIDEO_PATH, "rb") as f:
            files = {"file": (file_path.name, f, mime_type)}
            
            # Just test the upload part without actually sending
            print(f"   File name: {file_path.name}")
            print(f"   MIME type being sent: {mime_type}")
            
            # Now actually try the upload
            f.seek(0)  # Reset file pointer
            response = requests.post(f"{BASE_URL}/v1/analyze", files={"file": f})
            
            print(f"   Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"   Response body: {response.text}")
            else:
                print(f"   ✅ Upload successful!")
                print(f"   Response: {response.json()}")
                
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

def test_with_explicit_mime_type():
    """Test upload with explicit video MIME type"""
    
    print(f"\n🎯 Testing with explicit video/mp4 MIME type...")
    
    try:
        with open(VIDEO_PATH, "rb") as f:
            # Force the MIME type to be video/mp4
            files = {"file": (Path(VIDEO_PATH).name, f, "video/mp4")}
            response = requests.post(f"{BASE_URL}/v1/analyze", files=files)
            
            print(f"   Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"   Response body: {response.text}")
            else:
                print(f"   ✅ Upload successful with explicit MIME type!")
                print(f"   Response: {response.json()}")
                
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    debug_file_info()
    test_with_explicit_mime_type()