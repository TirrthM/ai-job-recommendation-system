import sys
import collections
import pymongo
from flask import Flask, render_template, request, jsonify
from config import MONGO_URI
from engine import RecommendationEngine

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder='static', template_folder='templates')
engine = RecommendationEngine()

def get_db():
    client = pymongo.MongoClient(MONGO_URI)
    return client, client['alumni_database']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    client, db = get_db()
    try:
        total_jobs = db['jobs'].count_documents({})
        total_profiles = db['profiles'].count_documents({})
        total_notifications = db['notifications'].count_documents({})

        # Extract top skills and role distributions
        jobs_cursor = db['jobs'].find({}, {"title": 1, "required_skills": 1, "location": 1, "experience_required": 1})
        role_counter = collections.Counter()
        skills_counter = collections.Counter()
        location_counter = collections.Counter()

        for j in jobs_cursor:
            title = j.get("title", "Unknown")
            role_counter[title] += 1
            loc = j.get("location", "Unknown")
            location_counter[loc] += 1
            skills_raw = j.get("required_skills", "")
            for s in skills_raw.replace(',', ' ').split():
                clean_s = s.strip()
                if clean_s and len(clean_s) > 1:
                    skills_counter[clean_s] += 1

        top_skills = [{"skill": k, "count": v} for k, v in skills_counter.most_common(10)]
        top_roles = [{"role": k, "count": v} for k, v in role_counter.most_common(6)]
        top_locations = [{"location": k, "count": v} for k, v in location_counter.most_common(5)]

        return jsonify({
            "total_jobs": total_jobs,
            "total_profiles": total_profiles,
            "total_notifications": total_notifications,
            "top_skills": top_skills,
            "top_roles": top_roles,
            "top_locations": top_locations,
            "classes": engine.classes
        })
    finally:
        client.close()

@app.route('/api/jobs')
def get_jobs():
    query = request.args.get('q', '').lower().strip()
    role = request.args.get('role', '').strip()
    client, db = get_db()
    try:
        jobs = list(db['jobs'].find({}, {"_id": 0}))
        if query:
            jobs = [
                j for j in jobs
                if query in j.get("title", "").lower()
                or query in j.get("company", "").lower()
                or query in j.get("required_skills", "").lower()
                or query in j.get("location", "").lower()
            ]
        if role:
            jobs = [j for j in jobs if j.get("title") == role]
        return jsonify(jobs)
    finally:
        client.close()

@app.route('/api/profiles')
def get_profiles():
    query = request.args.get('q', '').lower().strip()
    client, db = get_db()
    try:
        profiles = list(db['profiles'].find({}, {"_id": 0}))
        if query:
            profiles = [
                p for p in profiles
                if query in p.get("name", "").lower()
                or query in p.get("skills", "").lower()
                or query in p.get("location", "").lower()
            ]
        return jsonify(profiles)
    finally:
        client.close()

@app.route('/api/notifications')
def get_notifications():
    client, db = get_db()
    try:
        notifications = list(db['notifications'].find({}, {"_id": 0}))
        return jsonify(notifications[::-1])  # newest first
    finally:
        client.close()

@app.route('/api/notifications/clear', methods=['POST'])
def clear_notifications():
    client, db = get_db()
    try:
        db['notifications'].delete_many({})
        return jsonify({"success": True, "message": "All notifications cleared."})
    finally:
        client.close()

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.get_json() or {}
    skills = data.get('skills', '')
    bio = data.get('bio', '')
    experience = data.get('experience', 0)
    user_name = data.get('name', 'Interactive Candidate')
    save_notification = data.get('save_notification', True)

    result = engine.recommend(
        skills=skills,
        bio=bio,
        experience=experience,
        user_name=user_name,
        save_notification=save_notification
    )
    return jsonify(result)

@app.route('/api/run-batch', methods=['POST'])
def run_batch():
    results = engine.run_batch_recommendations()
    return jsonify({
        "success": True,
        "processed": len(results),
        "results": results
    })

if __name__ == '__main__':
    print("==========================================================")
    print("  🚀 AI Job Recommendation System Web Dashboard Running! ")
    print("  👉 Open http://127.0.0.1:5000 in your browser           ")
    print("==========================================================")
    app.run(host='127.0.0.1', port=5000, debug=False)
