from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.utils.html import escape
from .mongo import db


import time
from bson import ObjectId  # Add this import at top if not already present


import requests
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import google.generativeai as genai
import os
import json

from django.conf import settings
import hashlib

import uuid
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt



from datetime import datetime

from .mongo import chat_history_col




def test_mongo(request):
    try:
        # Insert a sample record
        db.test_collection.insert_one({"message": "MongoDB connected successfully!"})

        # Fetch one record
        record = db.test_collection.find_one({}, {"_id": 0})
        return JsonResponse({"status": "success", "data": record})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
    

# Create your views here.

def index(request):
    return render(request, 'chatbot/index.html')

def about(request):
    return render(request,'chatbot/about.html')

def chat(request):
    return render(request,'chatbot/chat.html')


def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        education = request.POST.get("education")
        keep_logged_in = "keep_logged_in" in request.POST

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # check if user already exists
        existing_user = db.users.find_one({"email": email})
        if existing_user:
            return render(request, "chatbot/signup.html", {"error": "Email already registered!"})

        # generate unique user_id
        user_id = f"USR-{int(time.time())}"

        # data to insert
        user_data = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password": hashed_password,
            "education": education,
            "keep_logged_in": keep_logged_in,
            "created_at": datetime.utcnow(),
        }

        db.users.insert_one(user_data)
        print(f"✅ New user created: {username} ({email})")

        return redirect("chatbot:signin")

    return render(request, "chatbot/signup.html")



def signin(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        user = db.users.find_one({"email": email, "password": hashed_password})

        if user:
            request.session["user_id"] = user["user_id"]
            request.session["user_name"] = user["username"]
            print(f"✅ Login successful for: {email}")
            return redirect("chatbot:dashboard")
        else:
            print(f"❌ Invalid login for: {email}")
            return render(request, "chatbot/signin.html", {"login_error": True})

    return render(request, "chatbot/signin.html")



def dashboard(request):
    user_name = request.session.get("user_name", "Guest")
    today = datetime.now().strftime("%A, %B %d, %Y")  # e.g., "Tuesday, October 22, 2025"
    return render(request, "chatbot/dashboard.html", {
        "user_name": user_name,
        "today": today
    })


def roadmap(request):
    user_name = request.session.get("user_name", "Guest")
    today = datetime.now().strftime("%A, %B %d, %Y")  # e.g., "Tuesday, October 22, 2025"
    return render(request, "chatbot/roadmap.html", {
        "user_name": user_name,
        "today": today
    })

def google_signin(request):
    if request.method == "POST":
        data = json.loads(request.body)
        print("Google Sign-In Data:", data)
        # Optionally create or log in user here
        return JsonResponse({"status": "success"})
    return JsonResponse({"error": "Invalid request"}, status=400)


API_KEY = settings.GOOGLE_GENAI_API_KEY
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

print("GOOGLE_GENAI_API_KEY =", API_KEY)


# CHAT_HISTORY_FILE = "result.json"
chat_history_col = db.chat_history

def getResponse(request):
    try:
        userMessage = request.GET.get('userMessage')
        user_name = request.session.get("user_name", "Guest")

        if not userMessage:
            return JsonResponse({"response": "No message received."})


        # Gemini model
        model = genai.GenerativeModel("gemini-2.5-flash")  # fast + free-tier
        response = model.generate_content([userMessage])
        bot_reply = response.candidates[0].content.parts[0].text

        # Save to MongoDB
        chat_history_col.insert_one({
            "user": user_name,
            "message": userMessage,
            "response": bot_reply,
            "timestamp": datetime.now()
        })
        print("✅ Message saved to MongoDB")

        return JsonResponse({"response": bot_reply})

    except Exception as e:
        print("❌ Error:", str(e))
        return JsonResponse({"response": "Sorry, something went wrong."})

def getChatHistory(request):
    user = request.session.get("user_name", "Guest")  # get from session
    history = list(chat_history_col.find({"user": user}, {"_id": 0}).sort("timestamp", 1))
    return JsonResponse({"history": history}, safe=False)




roadmaps_col = db["roadmaps"]


# -------------------- Generate Roadmap --------------------
@csrf_exempt                  
@require_POST                 
def generate_roadmap(request):
    try:
        # ---- Request data JSON se parse kar rahe hain ----
        body = json.loads(request.body)    # client se aaya JSON data python dict me convert
        user_name = request.session.get("user_name")  # current login user ka username

        
        goal = body.get("goal", "").strip()           
        timeframe = int(body.get("timeframe", 0))     
        timeunit = body.get("timeunit", "")           
        level = body.get("level", "")                 
        daily_time = float(body.get("dailyTime", 0))  

        # ---- Mandatory field validate ----
        if not goal:          # agar goal empty hai toh error bhej do
            return JsonResponse({"error": "Missing goal"}, status=400)

        # ---- AI Prompt create kar rahe hain taaki model sahi JSON roadmap create kare ----
        prompt = f"""
You are a helpful AI. ONLY respond with valid JSON. NO extra text.
Create a JSON study roadmap for "{goal}".
Level: {level}, Duration: {timeframe} {timeunit}, Daily Study Time: {daily_time} hours.

Format EXACTLY like this:
{{
    "title": "Your Study Plan",
    "totalHours": <int>,
    "weeks": [
        {{
            "id": 1,
            "title": "Week 1",
            "description": "Short summary",
            "tasks": [
                {{
                    "id": "task1",
                    "name": "Task Name",
                    "description": "Task details"
                }}
            ]
        }}
    ]
}}
Respond ONLY with JSON.
"""

        # ---- Yaha AI ko call kar rahe hain ----
        response = model.generate_content(prompt)
        text = response.text.strip()

        # ---- JSON output clean kar rahe hain (kabhi kabhi AI ```json format add kar deta hai) ----
        text = text.replace("```json", "").replace("```", "").strip()
        roadmap = json.loads(text)   # JSON string ko python dict me convert

        # ---- UUID generate kar rahe hain har roadmap ko uniquely identify karne ke liye ----
        roadmap_uuid = str(uuid.uuid4())

        # ---- Final document jo DB me save karna hai ----
        roadmap_doc = {
            "uuid": roadmap_uuid,          
            "user_name": user_name,        
            "roadmap": roadmap,            
            "progress": {},                
            "created_at": datetime.utcnow(), 
            "completed": False             
        }

    
        roadmaps_col.insert_one(roadmap_doc)

        return JsonResponse({**roadmap, "uuid": roadmap_uuid})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format in request"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



# -------------------- Get User Roadmaps --------------------

def get_user_roadmaps(request):
    user_name = request.session.get("user_name")
    roadmaps = list(roadmaps_col.find({"user_name": user_name}))

    # ✅ Get the last 5 roadmaps (most recent ones)
    roadmaps = roadmaps[-5:]  

    data = []
    for r in roadmaps:
        roadmap = r["roadmap"]
        total_tasks = sum(len(w["tasks"]) for w in roadmap["weeks"])
        completed_tasks = len(r.get("progress", {}))
        percentage = round((completed_tasks / total_tasks) * 100) if total_tasks else 0
        data.append({
            "uuid": r["uuid"],
            "title": roadmap["title"],
            "totalHours": roadmap["totalHours"],
            "percentage": percentage,
            "completed": r.get("completed", False)
        })

    return JsonResponse(data, safe=False)


# -------------------- Save Roadmap Progress --------------------
@csrf_exempt
@require_POST
def save_roadmap_progress(request):
    try:
        body = json.loads(request.body)
        uuid_ = body.get("uuid")
        progress = body.get("progress", {})

        roadmap_doc = roadmaps_col.find_one({"uuid": uuid_})
        if not roadmap_doc:
            return JsonResponse({"error": "Roadmap not found"}, status=404)

        total_tasks = sum(len(w["tasks"]) for w in roadmap_doc["roadmap"]["weeks"])
        completed_tasks = len(progress)
        completed_flag = completed_tasks == total_tasks

        roadmaps_col.update_one(
            {"uuid": uuid_},
            {"$set": {"progress": progress, "completed": completed_flag}}
        )

        msg = "Congratulations! You completed this roadmap!" if completed_flag else "Progress saved"
        return JsonResponse({"message": msg, "completed": completed_flag})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# -------------------- Delete Roadmap --------------------
@csrf_exempt
@require_POST
def delete_roadmap(request):
    try:
        body = json.loads(request.body)
        uuid_ = body.get("uuid")
        result = roadmaps_col.delete_one({"uuid": uuid_})
        if result.deleted_count == 0:
            return JsonResponse({"error": "Roadmap not found"}, status=404)
        return JsonResponse({"message": "Roadmap deleted successfully"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

def get_roadmap_details(request, uuid):
    roadmap = roadmaps_col.find_one({"uuid": uuid}, {"_id": 0})
    return JsonResponse(roadmap)


    
def quiz(request):
    return render(request, 'chatbot/quiz.html', {})


@csrf_exempt
def save_quiz_result(request):
    if request.method == "POST":
        data = json.loads(request.body)
        # You can save this in DB later, for now just return success
        print("Quiz result saved:", data)
        return JsonResponse({"status": "success"})
    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
@require_POST
def generate_quiz(request):
    try:
        # Parse incoming request
        body = json.loads(request.body)
        topic = body.get("topic", "").strip()

        # Input validation
        if not topic:
            return JsonResponse({"error": "Topic required"}, status=400)

        # Prepare strict prompt for AI
        prompt = f"""
You are a helpful AI. ONLY respond with valid JSON. NO extra text.
Generate 10 multiple choice questions (MCQs) on "{topic}".
Each question should have 4 options (A, B, C, D) and mark the correct answer as an index 0-3.

Format EXACTLY like this:
[
    {{
        "question": "Question text",
        "options": ["A", "B", "C", "D"],
        "correct": 0
    }}
]
Respond ONLY with JSON.
"""

        # Call Gemini API
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Strip any backticks ``` or ```json
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        if text.startswith("```"):
            text = text[3:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        # Parse AI JSON
        try:
            mcqs = json.loads(text)
        except json.JSONDecodeError:
            return JsonResponse({"error": "AI response was not valid JSON", "raw": text}, status=500)

        # Validate structure
        if not isinstance(mcqs, list):
            return JsonResponse({"error": "Invalid MCQ structure from AI"}, status=500)

        for q in mcqs:
            if "question" not in q or "options" not in q or "correct" not in q:
                return JsonResponse({"error": "Incomplete question data from AI"}, status=500)
            if not isinstance(q["options"], list) or len(q["options"]) != 4:
                q["options"] = ["Option A", "Option B", "Option C", "Option D"]
            if not isinstance(q["correct"], int):
                q["correct"] = 0

        return JsonResponse({
            "topic": topic,
            "questions": mcqs,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format in request"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



