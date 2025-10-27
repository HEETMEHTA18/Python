import PyPDF2
import re
import difflib

file_path = "sample.pdf"

def extract_pdf_text(pdf_path):
    """Extract original text and lowercase text from a PDF file."""
    original = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            original += page_text + "\n"
    return original, original.lower()

def find_name_candidates(original_text):
    """Find likely name strings from the PDF using multiple heuristics."""
    candidates = []

    # labeled fields: "Name: John Doe", "Applicant Name - John Doe"
    for match in re.findall(r'(?:name|applicant name|applicant|candidate|student)[\s:\-]+([A-Za-z ,.\'-]{2,120})', original_text, flags=re.I):
        candidates.append(match.strip())

    # Title-case sequences (common for printed names)
    for match in re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b', original_text):
        candidates.append(match.strip())

    # UPPERCASE sequences (e.g., CERTIFICATES with full-caps names)
    for match in re.findall(r'\b([A-Z]{2,}(?:\s+[A-Z]{2,}){1,3})\b', original_text):
        # normalize spacing and capitalize for readability
        candidates.append(match.strip().title())

    # deduplicate while keeping order
    seen = set()
    uniq = []
    for c in candidates:
        key = c.lower()
        if key and key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq

def normalize_name(s):
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

def best_name_match(user_name, candidates):
    """Return best candidate and similarity ratio (0..1) using SequenceMatcher."""
    user_n = normalize_name(user_name)
    best = ("", 0.0)
    for c in candidates:
        c_n = normalize_name(c)
        score = difflib.SequenceMatcher(None, user_n, c_n).ratio()
        if score > best[1]:
            best = (c, score)
    return best

def fuzzy_scan_windows(original_text, user_name, max_words=4):
    """Slide over the text words and try small phrases against user_name for best fuzzy score."""
    words = re.findall(r"[A-Za-z']+", original_text)
    user_n = normalize_name(user_name)
    best_phrase, best_score = "", 0.0
    n = len(words)
    for wlen in range(2, max_words + 1):
        for i in range(0, n - wlen + 1):
            phrase = " ".join(words[i:i + wlen])
            score = difflib.SequenceMatcher(None, user_n, normalize_name(phrase)).ratio()
            if score > best_score:
                best_phrase, best_score = phrase, score
    return best_phrase, best_score

def check_document(pdf_path, username, eligibility_keyword="eligible", threshold=0.70):
    original_text, lower_text = extract_pdf_text(pdf_path)

    # A: direct substring match (strong) on lowercase text
    A_direct = username.lower() in lower_text

    # find labeled/title/uppercase candidates and compute best similarity
    candidates = find_name_candidates(original_text)
    best_candidate, similarity = best_name_match(username, candidates)

    # also try sliding-window fuzzy scan over the document for missed names
    sw_phrase, sw_score = fuzzy_scan_windows(original_text, username, max_words=4)
    if sw_score > similarity:
        best_candidate, similarity = sw_phrase, sw_score

    # decide name match using threshold or direct match
    A = A_direct or (similarity >= threshold)

    # B: eligibility keyword (check lowercase)
    B = eligibility_keyword.lower() in lower_text if eligibility_keyword else True

    # Logical decision: admission allowed if both A and B
    Y = A and B

    # Discrete-math like summary (booleans -> integer)
    A_int = int(A)
    B_int = int(B)
    Y_int = int(Y)

    return {
        "username_provided": username,
        "A_direct_match": A_direct,
        "best_candidate": best_candidate,
        "similarity_score": round(similarity, 3),
        "A_name_match": A,
        "B_eligibility_present": B,
        "Admission_allowed_Y(A∧B)": Y,
        "A_int": A_int,
        "B_int": B_int,
        "Y_int": Y_int
    }

# Example usage
if __name__ == "__main__":
    pdf_file = input("PDF file path (default: sample.pdf): ").strip() or file_path
    user_input = input("Enter full name to verify: ").strip()
    eligibility_word = input("Eligibility keyword (default: eligible): ").strip() or "eligible"

    result = check_document(pdf_file, user_input, eligibility_word)
    print("\nResult summary:")
    print(f"- Username provided: {result['username_provided']}")
    print(f"- Direct substring match (A_direct): {result['A_direct_match']}")
    print(f"- Best candidate found: {result['best_candidate']} (similarity {result['similarity_score']})")
    print(f"- Name match decision (A): {result['A_name_match']}  [as int: {result['A_int']}]")
    print(f"- Eligibility present (B): {result['B_eligibility_present']}  [as int: {result['B_int']}]")
    print(f"- Admission allowed (Y = A ∧ B): {result['Admission_allowed_Y(A∧B)']}  [as int: {result['Y_int']}]")
