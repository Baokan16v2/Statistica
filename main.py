import streamlit as st
import random
import re
import os
from pypdf import PdfReader

# --- 1. CONFIGURARE FIȘIERE PDF ---
PDF_FILES = {
    "Capitolul 1": "cap1.pdf",
    "Capitolul 2": "cap2.pdf",
    "Capitolul 3": "cap3.pdf", 
    "Capitolul 4": "cap4.pdf"
}

# --- 2. PARSAREA PDF-ULUI ---
def parse_pdf_quiz(file_path):
    if not os.path.exists(file_path):
        return []

    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        st.error(f"Eroare la citirea PDF: {e}")
        return []

    lines = text.split('\n')
    questions = []
    
    current_q_text = []
    current_options = []
    correct_indices = []
    current_explanation = []
    
    state = "question" 
    
    # Modele RegEx pentru a găsi fix elementele de care avem nevoie:
    # 1. Opțiuni: a), b) etc. (Am pus (.*) pentru a prinde și cazurile unde textul variantei e pe rândul următor)
    opt_pattern = re.compile(r'^(@?)([a-zA-Z])\)\s*(.*)')
    
    # 2. Întrebare nouă: obligatoriu un număr urmat de punct și un spațiu (ex: "1. ", "16. ")
    question_pattern = re.compile(r'^\d+\.\s')
    
    # 3. Explicație: găsește sintagma "explicatie:" oriunde pe rând, ignorând majusculele și variațiile de diacritice
    explanation_pattern = re.compile(r'explica[tţț]ie\s*:', re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Ignorăm titlurile de pagini care pot apărea pe parcurs
        if line.lower().startswith("capitolul") or line.lower().startswith("grile") or line.lower().startswith("statistica"):
            continue

        # 1. Verificăm dacă este începutul unei întrebări noi
        if question_pattern.match(line):
            # Salvăm întrebarea anterioară (dacă există)
            if current_q_text and current_options:
                questions.append({
                    "text": " ".join(current_q_text).strip(),
                    "options": current_options,
                    "correct_indices": correct_indices,
                    "explanation": " ".join(current_explanation).strip()
                })
            
            # Resetăm listele pentru noua întrebare
            current_q_text = [line]
            current_options = []
            correct_indices = []
            current_explanation = []
            state = "question"
            continue

        # 2. Verificăm dacă rândul curent este o opțiune de răspuns
        opt_match = opt_pattern.match(line)
        if opt_match:
            state = "options"
            is_correct = bool(opt_match.group(1) == '@')
            opt_text = opt_match.group(3)
            
            if '@' in opt_text:
                is_correct = True
                opt_text = opt_text.replace('@', '').strip()
            
            current_options.append(opt_text)
            if is_correct:
                correct_indices.append(len(current_options) - 1)
            continue

        # 3. Verificăm dacă rândul conține sintagma cu explicația
        if explanation_pattern.search(line):
            state = "explanation"
            current_explanation.append(line)
            continue

        # 4. Dacă rândul nu este nici o opțiune, nici o întrebare, nici o explicație nouă
        # atunci reprezintă o continuare a textului din starea curentă:
        if state == "question":
            current_q_text.append(line)
        elif state == "options":
            if current_options:
                current_options[-1] += " " + line
        elif state == "explanation":
            current_explanation.append(line)
            
    # La finalul fișierului, adăugăm și ultima întrebare procesată
    if current_q_text and current_options:
        questions.append({
            "text": " ".join(current_q_text).strip(),
            "options": current_options,
            "correct_indices": correct_indices,
            "explanation": " ".join(current_explanation).strip()
        })

    return questions

# --- 3. FUNCȚII AUXILIARE ---
def restart_quiz():
    st.session_state.session_id += 1
    st.session_state.verified_questions = set()
    st.session_state.correct_answers = set()
    if 'questions' in st.session_state and st.session_state.questions:
        random.shuffle(st.session_state.questions)

def change_chapter():
    if 'questions' in st.session_state:
        del st.session_state['questions']
    restart_quiz()

# --- 4. INTERFAȚA PRINCIPALĂ ---
def main():
    st.set_page_config(page_title="Quiz Statistica", page_icon="📈", layout="wide")
    
    with st.sidebar:
        st.header("📂 Alege Capitolul")
        selected_chapter = st.selectbox(
            "Selectează PDF-ul din care vrei să dai testul:",
            list(PDF_FILES.keys()),
            on_change=change_chapter,
            key="chapter_selector"
        )
        
        st.markdown("---")
        
    st.title(f"📈 Test Grilă: {selected_chapter}")

    if 'questions' not in st.session_state:
        current_file = PDF_FILES[selected_chapter]
        raw_questions = parse_pdf_quiz(current_file)
        
        if raw_questions:
            random.shuffle(raw_questions)
            st.session_state.questions = raw_questions
        else:
            st.warning(f"Nu s-au găsit întrebări sau fișierul '{current_file}' lipsește. Te rog asigură-te că PDF-ul este în același folder cu scriptul.")
            st.stop()
            
    if 'session_id' not in st.session_state:
        st.session_state.session_id = 0
    if 'verified_questions' not in st.session_state:
        st.session_state.verified_questions = set()
    if 'correct_answers' not in st.session_state:
        st.session_state.correct_answers = set()

    sid = st.session_state.session_id
    total_questions = len(st.session_state.questions)
    verified_count = len(st.session_state.verified_questions)
    current_score = len(st.session_state.correct_answers)

    with st.sidebar:
        st.header("📊 Progres")
        if total_questions > 0:
            progres = verified_count / total_questions
            st.progress(progres)
            st.write(f"Întrebări completate: **{verified_count} / {total_questions}**")
            st.write(f"Răspunsuri corecte: **{current_score}**")
            
            if verified_count > 0:
                acc = (current_score / verified_count) * 100
                st.metric("Acuratețe momentană", f"{acc:.1f}%")
        
        st.markdown("---")
        st.button("🔄 Restart Test", on_click=restart_quiz)

    for i, q in enumerate(st.session_state.questions):
        
        with st.container():
            st.markdown(f"#### {q['text']}")
            
            selected_indices = []
            
            for idx, opt in enumerate(q['options']):
                chk_key = f"chk_{sid}_{i}_{idx}"
                is_disabled = i in st.session_state.verified_questions
                
                checked = st.checkbox(opt, key=chk_key, disabled=is_disabled)
                if checked:
                    selected_indices.append(idx)

            if i not in st.session_state.verified_questions:
                if st.button(f"Verifică întrebarea {i+1}", key=f"btn_check_{sid}_{i}"):
                    st.session_state.verified_questions.add(i)
                    
                    if q['correct_indices']:
                        if sorted(selected_indices) == sorted(q['correct_indices']):
                            st.session_state.correct_answers.add(i)
                    
                    st.rerun()
            
            if i in st.session_state.verified_questions:
                correct_indices = q['correct_indices']
                
                if not correct_indices:
                    st.warning("⚠️ Această întrebare nu are răspunsul marcat în PDF (lipsește @).")
                else:
                    if sorted(selected_indices) == sorted(correct_indices):
                        st.success("✅ Corect!")
                    else:
                        correct_texts = [q['options'][idx] for idx in correct_indices]
                        st.error("❌ Greșit.")
                        st.info(f"**Răspuns corect:** {', '.join(correct_texts)}")
                
                if q.get('explanation'):
                    st.info(f"💡 **{q['explanation']}**")
            
            st.markdown("---")

    if verified_count == total_questions and total_questions > 0:
        
        valid_total = sum(1 for q in st.session_state.questions if q['correct_indices'])
        final_percentage = (current_score / valid_total) * 100 if valid_total > 0 else 0

        st.markdown("""
        <div style="background-color:#d4edda;padding:20px;border-radius:10px;border:2px solid #c3e6cb">
            <h2 style="color:#155724;text-align:center;">🏆 TEST COMPLETAT!</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Scor Final", f"{current_score} / {valid_total}")
        col2.metric("Procentaj", f"{final_percentage:.2f}%")
        
        if final_percentage >= 50:
            st.balloons()
            col3.success("AI PROMOVAT!")
        else:
            col3.error("MAI ÎNCEARCĂ...")

if __name__ == "__main__":
    main()