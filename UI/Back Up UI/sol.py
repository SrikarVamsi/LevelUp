from flask import Flask, request, render_template_string, send_file, session, redirect, url_for
import io
import json
from fpdf import FPDF
import google.generativeai as genai
from tavily import TavilyClient
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app and set a secret key for session storage
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Initialize Tavily client with API key
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Configure Gemini (Google Generative AI) API key and model
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
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

# HTML template with enhanced CSS styling, a loading overlay, and a footer
TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Youth Employability</title>
    <!-- Font Awesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        /* Background styling */
        body {
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #ffe6e6, #fff5e6);
            margin: 0;
            padding: 0;
            color: #333;
        }
        /* Container styling */
        .container {
            display: flex;
            flex-wrap: wrap;
            width: 90%;
            max-width: 1200px;
            margin: 30px auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .left, .right {
            padding: 30px;
        }
        .left {
            flex: 2;
            border-right: 1px solid #eee;
        }
        .right {
            flex: 1;
            min-width: 300px;
        }
        h1, h2 {
            color: #b30059;
            text-align: center;
        }
        form {
            margin-bottom: 30px;
        }
        label {
            font-weight: bold;
            color: #b30059;
        }
        input[type="text"], textarea {
            width: calc(100% - 12px);
            padding: 6px;
            margin-top: 5px;
            margin-bottom: 15px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        input[type="submit"], .download-btn {
            background-color: #b30059;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            display: inline-block;
            margin: 5px 0;
        }
        input[type="submit"]:hover, .download-btn:hover {
            background-color: #99004d;
        }
        .job {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
        }
        .job:last-child {
            border-bottom: none;
        }
        .job a {
            text-decoration: none;
            color: #b30059;
            font-weight: bold;
        }
        .explanation {
            background-color: #fff0f5;
            border-left: 4px solid #b30059;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            white-space: pre-wrap;
        }
        /* Chat window styling */
        .chat-container {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background-color: #f9f9f9;
            display: flex;
            flex-direction: column;
            height: 500px;
        }
        .chat-log {
            flex: 1;
            overflow-y: auto;
            border: 1px solid #eee;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #fff;
        }
        .chat-entry {
            margin: 5px 0;
        }
        .chat-entry.user {
            text-align: right;
            color: #0066cc;
        }
        .chat-entry.bot {
            text-align: left;
            color: #b30059;
        }
        /* Footer styling */
        .footer {
            text-align: center;
            padding: 10px;
            font-size: 14px;
            color: #666;
        }
        /* Loading overlay styling */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255,255,255,0.8);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            font-size: 24px;
            color: #b30059;
        }
    </style>
</head>
<body>
    <div class="loading-overlay" id="loading-overlay">
        <div><i class="fa-solid fa-spinner fa-spin"></i> We are searching for you...</div>
    </div>
    <div class="container">
        <div class="left">
            <h1><i class="fa-solid fa-briefcase"></i> Youth Employability</h1>
            <form method="post" onsubmit="showLoading()">
                <label for="job_title">Job Title:</label><br>
                <input type="text" name="job_title" id="job_title" placeholder="e.g., Cook, Maid" required><br>
                
                <label for="location">Preferred Location:</label><br>
                <input type="text" name="location" id="location" placeholder="City or region" required><br>
                
                <label for="age">Age:</label><br>
                <input type="text" name="age" id="age" placeholder="Your age"><br>
                
                <label for="education">Highest Educational Qualification:</label><br>
                <input type="text" name="education" id="education" placeholder="e.g., High School, Diploma" required><br>
                
                <label for="experience">Years of Experience:</label><br>
                <input type="text" name="experience" id="experience" placeholder="e.g., 3" required><br>
                
                <input type="submit" value="Search Jobs" id="submit-btn">
            </form>
            
            {% if job_suggestions %}
            <hr>
            <h2>Job Suggestions</h2>
            {% for job in job_suggestions %}
                <div class="job">
                    <strong>{{ job['title'] }}</strong> &nbsp;
                    <a href="{{ job['url'] }}" target="_blank">
                        <i class="fa-solid fa-up-right-from-square"></i> View Details
                    </a>
                    <div class="explanation">
                        <p>{{ job['summary'] }}</p>
                    </div>
                </div>
            {% endfor %}
            <div style="text-align: center;">
                <a href="{{ url_for('download_jobs') }}" class="download-btn">
                    <i class="fa-solid fa-download"></i> Download Job Details as PDF
                </a>
            </div>
            {% endif %}
            <div class="footer">
                Made with ❤️ by LevelUp
            </div>
        </div>
        <div class="right">
            <h2>Chat with Us</h2>
            <div class="chat-container">
                <div id="chat-log" class="chat-log">
                    {% for message in chat_history %}
                        <div class="chat-entry {{ message['sender'] }}">
                            <strong>{{ message['sender']|capitalize }}:</strong> {{ message['text'] }}
                        </div>
                    {% endfor %}
                </div>
                <form id="chat-form" method="post" action="{{ url_for('chat') }}">
                    <textarea name="chat_message" id="chat_message" rows="2" placeholder="Ask about any job details..." required></textarea>
                    <input type="submit" value="Send">
                </form>
            </div>
            <div class="footer">
                Made with ❤️ by LevelUp
            </div>
        </div>
    </div>
    
    <script>
        function showLoading() {
            document.getElementById("loading-overlay").style.display = "flex";
            document.getElementById("submit-btn").disabled = true;
        }
    </script>
</body>
</html>
'''

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
        
    return render_template_string(TEMPLATE, 
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
