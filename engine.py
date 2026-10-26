import json
import pymongo
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import LabelEncoder
from config import MONGO_URI

class RecommendationEngine:
    def __init__(self, mongo_uri=MONGO_URI):
        self.mongo_uri = mongo_uri
        self.vectorizer = None
        self.label_encoder = None
        self.model = None
        self.jobs = []
        self.users = []
        self.classes = []
        self.train()

    def get_db(self):
        client = pymongo.MongoClient(self.mongo_uri)
        return client, client['alumni_database']

    def train(self):
        client, db = self.get_db()
        try:
            self.jobs = list(db['jobs'].find({}, {"_id": 0}))
            self.users = list(db['profiles'].find({}, {"_id": 0}))
        finally:
            client.close()

        if not self.jobs:
            # Fallback to local jobs.json if DB is empty
            try:
                with open('jobs.json', 'r', encoding='utf-8') as f:
                    self.jobs = json.load(f)
            except Exception:
                self.jobs = []

        if not self.users:
            try:
                with open('profiles.json', 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except Exception:
                self.users = []

        job_texts = []
        job_labels = []

        for job in self.jobs:
            skills = job.get("required_skills", "")
            exp_required = str(job.get("experience_required", "0"))
            if skills:
                job_texts.append(f"{skills} {exp_required}")
                job_labels.append(job.get("title", "Unknown"))

        if not job_texts:
            raise ValueError("No valid jobs available for training!")

        self.vectorizer = TfidfVectorizer(stop_words="english", min_df=1)
        X_train = self.vectorizer.fit_transform(job_texts)

        self.label_encoder = LabelEncoder()
        y_train = self.label_encoder.fit_transform(job_labels)
        self.classes = list(self.label_encoder.classes_)

        self.model = MultinomialNB()
        self.model.fit(X_train, y_train)

    def recommend(self, skills, bio="", experience=0, user_name="Guest User", save_notification=True):
        if isinstance(skills, list):
            skills_str = " ".join(skills)
        else:
            skills_str = str(skills or "")

        bio_str = str(bio or "").strip()
        user_exp = int(experience or 0)
        user_text = f"{skills_str} {bio_str}".strip()

        if not user_text:
            return {
                "success": False,
                "error": "Please provide skills or a bio for recommendation."
            }

        X_test = self.vectorizer.transform([user_text])
        predicted_idx = self.model.predict(X_test)[0]
        recommended_title = self.label_encoder.inverse_transform([predicted_idx])[0]

        # Calculate prediction probabilities for confidence scores
        probs = self.model.predict_proba(X_test)[0]
        top_indices = np.argsort(probs)[::-1][:3]
        top_predictions = [
            {
                "title": self.label_encoder.inverse_transform([idx])[0],
                "confidence": round(float(probs[idx]) * 100, 1)
            }
            for idx in top_indices
        ]

        # Search matching jobs and check experience constraint
        matching_jobs = []
        user_skill_tokens = set([s.strip().lower() for s in skills_str.replace(',', ' ').split() if s.strip()])

        for job in self.jobs:
            job_exp = int(job.get("experience_required", "0") or 0)
            if job.get("title") == recommended_title:
                job_skills_raw = job.get("required_skills", "")
                job_skill_tokens = set([s.strip().lower() for s in job_skills_raw.replace(',', ' ').split() if s.strip()])
                common_skills = list(user_skill_tokens.intersection(job_skill_tokens))

                is_exp_qualified = user_exp >= job_exp

                job_info = {
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "description": job.get("description"),
                    "required_skills": job_skills_raw,
                    "experience_required": job_exp,
                    "is_qualified": is_exp_qualified,
                    "matched_skills": common_skills
                }
                matching_jobs.append(job_info)

        # Filter strictly qualified jobs for official recommendation
        qualified_jobs = [j for j in matching_jobs if j["is_qualified"]]
        best_match = qualified_jobs[0] if qualified_jobs else None

        notification_saved = False
        if best_match and save_notification:
            client, db = self.get_db()
            try:
                notification = {
                    "user_name": user_name,
                    "job_title": best_match["title"],
                    "company": best_match["company"],
                    "location": best_match["location"],
                    "description": best_match["description"],
                    "status": "unread"
                }
                db.notifications.insert_one(notification)
                notification_saved = True
            except Exception as e:
                print("Could not save notification:", e)
            finally:
                client.close()

        return {
            "success": True,
            "predicted_role": recommended_title,
            "confidence": top_predictions[0]["confidence"] if top_predictions else 0,
            "top_predictions": top_predictions,
            "best_match": best_match,
            "all_role_matches": matching_jobs,
            "has_experience_conflict": len(matching_jobs) > 0 and len(qualified_jobs) == 0,
            "notification_saved": notification_saved
        }

    def run_batch_recommendations(self):
        client, db = self.get_db()
        try:
            users = list(db['profiles'].find({}, {"_id": 0}))
        finally:
            client.close()

        results = []
        for user in users:
            rec = self.recommend(
                skills=user.get("skills", ""),
                bio=user.get("bio", ""),
                experience=user.get("experience", 0),
                user_name=user.get("name", "Unknown"),
                save_notification=True
            )
            results.append({
                "user": user.get("name"),
                "skills": user.get("skills"),
                "experience": user.get("experience"),
                "recommended_role": rec.get("predicted_role"),
                "matched": rec.get("best_match") is not None
            })
        return results
