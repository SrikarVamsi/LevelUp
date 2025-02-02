from flask import Flask, request, render_template, send_file, session, redirect, url_for
import io
import json
from fpdf import FPDF
import google.generativeai as genai
from tavily import TavilyClient

# Initialize Flask app and set a secret key for session storage
app = Flask(__name__)
app.secret_key = 'your-very-secret-key'

# Initialize Tavily client with API key
api_key = "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"
client = TavilyClient(api_key=api_key)

# Configure Gemini (Google Generative AI) API key and model
genai.configure(api_key="AIzaSyD5OddKQ4_3ynfymwv2chepY02ZDaGL6cs")
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Stub function for Microsoft 53 model summary (replace with an actual API call if available)
def generate_summary(job):
    summary = (f"Opportunity: {job.get('title', 'N/A')}\n"
               f"Explore details at: {job.get('url', '#')}\n"
               f"This role is perfect for building essential skills.")
    return summary

# Custom PDF class with header and footer for a professional look
class PDF(FPDF):
    def header(self):
        # Set a header with a fill color and title
        self.set_fill_color(70, 130, 180)  # Steel blue fill
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, "Job Details", ln=True, align="C", fill=True)
        self.ln(5)
        self.set_text_color(0, 0, 0)  # Reset to black

    def footer(self):
        # Position at 15 mm from bottom
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        # Replace the emoji with plain text to avoid Unicode issues
        self.cell(0, 10, "Made with love by LevelUp", 0, 0, 'C')

# Global variable for chat history (for demonstration only)
chat_history = []

@app.route('/', methods=['GET', 'POST'])
def index():
    job_suggestions = []
    global chat_history

    if request.method == 'POST':
        # Gather user input from the form
        user_data = {
            "job_title": request.form.get('job_title'),
            "location": request.form.get('location'),
            "age": request.form.get('age'),
            "education": request.form.get('education'),
            "experience": request.form.get('experience'),
        }
        
        # Build the search query
        query = (f"{user_data['job_title']} jobs in {user_data['location']} "
                 f"for {user_data['education']} with {user_data['experience']} years of experience")
        
        # Query Tavily for job suggestions
        response = client.search(query=query, max_results=7, topic="general")
        results = response.get("results", [])
        
        # For each job suggestion, generate a 2-3 line summary using the stub
        for job in results:
            summary = generate_summary(job)
            job['summary'] = summary
            job_suggestions.append(job)
        
        # Save job suggestions in session as JSON (for PDF download)
        session['job_suggestions'] = json.dumps(job_suggestions)
        
    return render_template('index.html', 
                          job_suggestions=job_suggestions,
                          chat_history=chat_history)

@app.route('/download')
def download_jobs():
    # Get job suggestions from session
    job_data = session.get('job_suggestions')
    if not job_data:
        return redirect(url_for('index'))
    job_suggestions = json.loads(job_data)
    
    # Create a PDF using our custom PDF class
    pdf = PDF()
    pdf.add_page()
    
    # Use built-in "Arial" font (Latin-1)
    pdf.set_font("Arial", "", 12)
    
    for job in job_suggestions:
        # Process text to replace unsupported Unicode characters
        safe_title = job.get('title', 'No Title').encode('latin-1', 'replace').decode('latin-1')
        safe_summary = job.get('summary', '').encode('latin-1', 'replace').decode('latin-1')
        
        # Job Title
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, safe_title, ln=True)
        pdf.ln(1)
        
        # Job Details with clickable link
        pdf.set_font("Arial", '', 12)
        pdf.cell(30, 10, "Details:", ln=0)
        url = job.get('url', 'No URL')
        pdf.set_text_color(0, 0, 255)  # Blue color for links
        pdf.cell(0, 10, "Click Here", ln=True, link=url)
        pdf.set_text_color(0, 0, 0)    # Reset to black
        
        # Job Summary
        pdf.multi_cell(0, 8, f"Summary: {safe_summary}")
        pdf.ln(5)
    
    # Instead of passing a BytesIO to output(), use dest='S' to get a string
    pdf_data = pdf.output(dest='S').encode('latin-1', 'replace')
    pdf_buffer = io.BytesIO(pdf_data)
    pdf_buffer.seek(0)
    
    return send_file(pdf_buffer,
                     mimetype='application/pdf',
                     as_attachment=True,
                     download_name='job_details.pdf')

@app.route('/chat', methods=['POST'])
def chat():
    global chat_history
    user_message = request.form.get('chat_message', '')
    if user_message:
        # Append user's message to chat history
        chat_history.append({'sender': 'user', 'text': user_message})
        
        # Prepare Gemini prompt (using your snippet style)
        prompt = (f"User asked: {user_message}\n\n"
                  "Based on the available job details and context, please provide a concise, helpful response in 2-3 lines.")
        response = gemini_model.generate_content(prompt)
        bot_reply = response.text if response and response.text else "Sorry, I couldn't generate a response."
        
        chat_history.append({'sender': 'bot', 'text': bot_reply})
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)