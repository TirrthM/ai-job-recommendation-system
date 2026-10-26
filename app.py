import sys
import collections
import pymongo
from flask import Flask, render_template, request, jsonify
from config import MONGO_URI
from engine import RecommendationEngine

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['TEMPLATES_AUTO_RELOAD'] = True
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
        notifications = list(db['notifications'].find({}))
        for n in notifications:
            n['_id'] = str(n['_id'])
        return jsonify(notifications[::-1])  # newest first
    finally:
        client.close()

@app.route('/api/notifications/clear', methods=['POST', 'GET'])
def clear_notifications():
    client, db = get_db()
    try:
        db['notifications'].delete_many({})
        return jsonify({"success": True, "message": "All notifications cleared."})
    finally:
        client.close()

@app.route('/api/notification-detail')
def notification_detail():
    """Return enriched notification with full user profile and full job details.
    Uses notif_id, user_name, job_title, company, and location to ensure 100% exact job match.
    For new users not in DB, reconstructs profile from candidate fields saved in notification.
    """
    notif_id     = request.args.get('notif_id', '').strip()
    user_name    = request.args.get('user_name', '').strip()
    job_title    = request.args.get('job_title', '').strip()
    company      = request.args.get('company', '').strip()
    job_location = request.args.get('job_location', '').strip() or request.args.get('location', '').strip()

    client, db = get_db()
    try:
        # 1. Try to find the exact notification document
        notif = None
        if notif_id:
            try:
                from bson import ObjectId
                notif = db['notifications'].find_one({"_id": ObjectId(notif_id)})
            except Exception:
                pass

        if not notif and user_name:
            query = {"user_name": user_name}
            if job_title:
                query["job_title"] = job_title
            if company:
                query["company"] = company
            if job_location:
                query["location"] = job_location
            notif = db['notifications'].find_one(query, sort=[("_id", -1)])

        if not notif and user_name and job_title:
            notif = db['notifications'].find_one(
                {"user_name": user_name, "job_title": job_title},
                sort=[("_id", -1)]
            )

        if not notif and user_name:
            notif = db['notifications'].find_one({"user_name": user_name}, sort=[("_id", -1)])

        # 2. Try to find a proper profile in the profiles collection
        profile = db['profiles'].find_one({"name": user_name}, {"_id": 0})

        # 3. If no DB profile, reconstruct from notification's stored candidate fields
        if not profile and notif:
            profile = {
                "name":       notif.get("user_name", user_name),
                "skills":     notif.get("candidate_skills", ""),
                "experience": notif.get("candidate_experience", 0),
                "location":   notif.get("candidate_location", ""),
                "bio":        notif.get("candidate_bio", ""),
                "email":      "(not in database)",
            }

        # 4. Find the matched job using title, company, AND location
        target_loc = job_location or (notif.get("location") if notif else None)
        target_title = job_title or (notif.get("job_title") if notif else None)
        target_company = company or (notif.get("company") if notif else None)

        job = None
        if target_title and target_company and target_loc:
            job = db['jobs'].find_one({
                "title": target_title,
                "company": target_company,
                "location": target_loc
            }, {"_id": 0})

        if not job and target_title and target_loc:
            job = db['jobs'].find_one({
                "title": target_title,
                "location": target_loc
            }, {"_id": 0})

        if not job and target_title and target_company:
            job = db['jobs'].find_one({
                "title": target_title,
                "company": target_company
            }, {"_id": 0})

        if not job and target_title:
            job = db['jobs'].find_one({"title": target_title}, {"_id": 0})

        # Fallback to the job data snapshot saved directly in the notification
        if not job and notif:
            job = {
                "title":               notif.get("job_title"),
                "company":             notif.get("company"),
                "location":            notif.get("location"),
                "description":         notif.get("description"),
                "required_skills":     notif.get("required_skills", ""),
                "experience_required": notif.get("experience_required", 0),
            }
        elif job and notif:
            # Guarantee the displayed job location and description match the notification
            if notif.get("location"):
                job["location"] = notif.get("location")
            if notif.get("description"):
                job["description"] = notif.get("description")
            if not job.get("required_skills") and notif.get("required_skills"):
                job["required_skills"] = notif.get("required_skills")
            if not job.get("experience_required") and notif.get("experience_required") is not None:
                job["experience_required"] = notif.get("experience_required")

        return jsonify({
            "profile": profile or {},
            "job":     job or {}
        })
    finally:
        client.close()

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.get_json() or {}
    skills            = data.get('skills', '')
    bio               = data.get('bio', '')
    experience        = data.get('experience', 0)
    user_name         = data.get('name', 'Interactive Candidate')
    location          = data.get('location', '')
    save_notification = data.get('save_notification', True)

    result = engine.recommend(
        skills=skills,
        bio=bio,
        experience=experience,
        user_name=user_name,
        location=location,
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
