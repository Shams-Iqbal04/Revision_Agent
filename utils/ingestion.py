import io
import pypdf

def extract_text_from_file(uploaded_file):
    if uploaded_file is None:
        return ""
    
    file_name = uploaded_file.name.lower()
    
    if file_name.endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(uploaded_file)
            extracted_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text.append(text)
            return "\n".join(extracted_text)
        except Exception as e:
            return f"Error reading PDF: {e}"
            
    elif file_name.endswith(".txt") or file_name.endswith(".md"):
        try:
            return uploaded_file.getvalue().decode("utf-8")
        except Exception as e:
            return f"Error reading text file: {e}"
            
    return ""
