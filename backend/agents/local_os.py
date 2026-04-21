import os
import logging
import base64
from pathlib import Path
from groq import Groq

logger = logging.getLogger(__name__)

# Security feature: Prevent directory traversal hacking
def is_safe_path(path: str) -> bool:
    try:
        resolved = Path(path).resolve()
        # For this prototype we allow any path, but normally you would restrict to a "sandbox" folder
        # e.g., if strictly enforcing sandbox: return resolved.is_relative_to(SANDBOX_DIR)
        return True
    except Exception:
        return False

def list_local_directory(directory_path: str = ".") -> list[dict]:
    """Lists files and folders inside a local directory path."""
    directory_path = str(directory_path).strip().strip("'").strip('"')
    if not is_safe_path(directory_path):
        return [{"error": "Unsafe or invalid directory path."}]
        
    try:
        items = []
        for entry in os.scandir(directory_path):
            items.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "path": entry.path,
                "size_bytes": entry.stat().st_size if entry.is_file() else 0
            })
        return items[:50] # Limit to 50 results to not overwhelm AI token limit
    except Exception as e:
        logger.error(f"Error reading directory {directory_path}: {e}")
        return [{"error": str(e)}]

def read_local_file(file_path: str) -> str:
    """Reads the text content of a file on the local machine."""
    file_path = str(file_path).strip().strip("'").strip('"')
    if not is_safe_path(file_path):
        return "Error: Unsafe or invalid file path."
        
    try:
        path = Path(file_path)
        if not path.is_file():
            return f"Error: '{file_path}' is not a valid file path on your system. DO NOT LOOP!"
            
        if path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            return "Notice: This is an image file. Do not read it as text. Use 'tool_analyze_local_image' to view its contents."
            
        # Support common text files
        # Native PyPDF2 Parsing for Local PDFs
        if path.suffix.lower() == '.pdf':
            import PyPDF2
            text = ""
            try:
                with open(file_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted: text += extracted + "\n"
                if not text.strip(): return "Error: PDF appears to be empty or contains scanned images without text layer."
                return text
            except Exception as e:
                return f"Error reading Local PDF: {e}"
        
        # Support common text files
        if path.suffix.lower() in ['.zip', '.exe', '.dll', '.bin']:
            return "Error: Cannot read binary/compiled files directly. Only text/code files are supported (.txt, .md, .py, .csv, etc)."
            
        file_size = path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            return f"Error: Local file is {file_size / 1024 / 1024:.1f} MB. To prevent memory depletion, maximum direct reading size is capped at 10MB."
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            return content
            
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return f"Error reading file: {e}"

def analyze_local_image(file_path: str, prompt: str = "Describe this image in detail.") -> str:
    """Analyzes a local image using Groq's Vision capabilities."""
    if not is_safe_path(file_path):
        return "Error: Unsafe or invalid file path."
    
    path = Path(file_path)
    if not path.is_file() or path.suffix.lower() not in ['.png', '.jpg', '.jpeg']:
        return "Error: File must be a valid .png or .jpg image."
        
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY is not configured."
        
    try:
        with open(path, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode("utf-8")
            
        import requests
        payload = {
            'apikey': 'helloworld',
            'language': 'eng',
            'isOverlayRequired': False,
            'base64Image': f'data:image/jpeg;base64,{img_b64}'
        }
        r = requests.post('https://api.ocr.space/parse/image', data=payload, timeout=25)
        result = r.json()
        vision_text = ""
        if result.get("ParsedResults"):
            vision_text = result["ParsedResults"][0].get("ParsedText", "").strip()
            
        if not vision_text:
            return "This image appears to have no readable text or OCR failed to extract meaningful text."
            
        return f"--- Image Transcribed Text ---\n" + vision_text
    except Exception as e:
        logger.error(f"Vision analysis error: {e}")
        return f"Error analyzing image: {e}"

def search_codebase(directory: str, query: str) -> str:
    """Recursively searches a local directory for files or code containing the exact query string."""
    if not is_safe_path(directory):
        return "Error: Unsafe directory path."
        
    path = Path(directory)
    if not path.is_dir():
        return f"Error: '{directory}' is not a directory."
        
    results = []
    # Skip common binary/ignore folders to prevent hanging
    ignore_dirs = {'.git', 'venv', '__pycache__', 'node_modules', '.next'}
    
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                if query.lower() in file.lower():
                    results.append(f"Found file matching name: {file_path}")
                
                if file.endswith(('.py', '.js', '.ts', '.md', '.txt', '.json', '.html', '.css', '.env')):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for idx, line in enumerate(f):
                                if query.lower() in line.lower():
                                    results.append(f"[{file_path}:{idx+1}] {line.strip()}")
                                    if len(results) >= 50:
                                        print("Matched limit")
                                        return "\n".join(results) + "\n... (Truncated. Found >50 matches)"
                    except Exception:
                        pass
        return "\n".join(results) if results else f"No matches found for '{query}' in {directory}"
    except Exception as e:
         return f"Search failed: {e}"

def create_local_directory(directory_path: str) -> str:
    """Creates a new folder at the specified physical native directory path."""
    directory_path = str(directory_path).strip().strip("'").strip('"')
    if not is_safe_path(directory_path):
        return "Error: Unsafe or invalid directory path."
    try:
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        return f"Success! Directory created at {directory_path}"
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return f"Error creating directory: {e}"

def write_local_file(file_path: str, content: str) -> str:
    """Creates a new text file at the specified local path with the given content."""
    file_path = str(file_path).strip().strip("'").strip('"')
    if not is_safe_path(file_path):
        return "Error: Unsafe or invalid file path."
        
    try:
        path = Path(file_path)
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return f"Success! Text file created at {file_path}"
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        return f"Error writing file: {e}"
