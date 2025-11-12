import google.generativeai as genai
import os
# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def get_subtopics(heading):
    prompt = f"List 8 important and distinct subtopics related to '{heading}'. Format them as a numbered list, one per line."
    response = model.generate_content(prompt)
    subtopics = response.text.strip().split('\n')
    return [line.split('. ', 1)[-1].strip() for line in subtopics if line.strip()]

def get_notes(subtopics):
    prompt = "Generate clear, educational notes on the following subtopics:\n\n"
    for i, topic in enumerate(subtopics, start=1):
        prompt += f"{i}. {topic}\n"
    response = model.generate_content(prompt)
    return response.text
