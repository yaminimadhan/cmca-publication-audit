from app.services.similarity_search import search_sentences
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

import os
import openai

client = OpenAI(api_key= os.getenv("OPENAI_API_KEY"))

def build_prompt(query_sentence, matches):
    top_match, top_score = matches[0]
    return f"""
You are acting as a **research compliance auditor**.
Your role is to verify whether a given sentence from a scientific document constitutes a **formal acknowledgement** of institutional or financial support.

**Extracted Sentence:**
"{query_sentence}"

This sentence was selected because it closely matches known acknowledgement phrases:
- "{top_match}" (Similarity: {top_score:.2f})

### Your task
Determine whether the sentence contains a **formal acknowledgement** that refers specifically to **one or more of the following entities**:
- CMCA (Centre for Microscopy Characterisation and Analysis)
- The University of Western Australia (UWA)
- Microscopy Australia or its nodes
- NCRIS (National Collaborative Research Infrastructure Strategy)

### Decision Criteria
Classify as a **formal acknowledgement** only if it clearly refers to:
- Use/access of CMCA/UWA microscopy facilities
- Technical or analytical assistance by these institutions
- NCRIS or Microscopy Australia support

Do **not** classify if:
- It only thanks individuals
- It expresses generic gratitude with no link to facilities, funding, or institutional support

### Respond in this exact format:
Answer: [Yes or No]  
Reason: (1–3 lines)
""".strip()


async def run_llm_verification_from_json(extractor_json: dict, top_k=7, threshold=0.70) -> dict:
    """
    Runs the LLM acknowledgement verification using structured sentence JSON from extractor.
    """
    raw_sentences = extractor_json.get("sentences", [])
    if not raw_sentences:
        return {"cmca_result": "No", "cosine_similarity": 0.0}

    # Extract plain text for similarity search
    sentences_text = [s.get("text", "") for s in raw_sentences if isinstance(s, dict) and "text" in s]

    # Run retrieval logic
    results = search_sentences(sentences_text, k=3)

    # Filter by similarity threshold
    filtered_results = {
        query: [(match, score) for (match, score) in matches if score >= threshold]
        for query, matches in results.items()
        if any(score >= threshold for (_, score) in matches)
    }

    # Sort by best similarity
    ranked_queries = [
        (query_sentence, matches, max(score for _, score in matches))
        for query_sentence, matches in filtered_results.items()
    ]
    ranked_queries.sort(key=lambda triple: triple[2], reverse=True)

    # Prepare response containers
    top_queries = ranked_queries[:top_k]
    llm_responses = []
    max_score = 0.0
    any_yes = False

    # Process each query with GPT-4
    for query_sentence, matches, best_score in top_queries:
        prompt = build_prompt(query_sentence, matches)

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research auditor."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
        except openai.RateLimitError:
            # Fallback or fail gracefully
            print("Quota exceeded: falling back to gpt-3.5-turbo...")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a research auditor."},
                    {"role": "user", "content": prompt}
                ],               
                temperature=0.0
            )

        answer_text = response.choices[0].message.content.strip()

        max_score = max(max_score, best_score)
        if "Answer: Yes" in answer_text:
            any_yes = True

        # find metadata (page/id/index) from extractor JSON
        meta = next((s for s in raw_sentences if s.get("text") == query_sentence), {})
        llm_responses.append({
            "sentence_id": meta.get("id"),
            "page": meta.get("page"),
            "index": meta.get("index"),
            "query_text": query_sentence,
            "similarity_score": round(best_score, 4),
            "llm_response": answer_text
        })

    # Final summary
    return {
        "cmca_result": "Yes" if any_yes else "No",
        "cosine_similarity": round(max_score, 4),
        "Sentence_verifications": llm_responses
    }
