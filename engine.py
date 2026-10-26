import json
import pymongo
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import LabelEncoder
from config import MONGO_URI


# ──────────────────────────────────────────────────────────────
#  SKILL ONTOLOGY & SYNONYM MAPPING (Semantic Skill Bridging)
# ──────────────────────────────────────────────────────────────
SKILL_RELATIONS = {
    # Web & Frontend Development
    "javascript": ["react", "node.js"],
    "js": ["react", "node.js"],
    "typescript": ["react", "node.js"],
    "ts": ["react", "node.js"],
    "html": ["react"],
    "css": ["react"],
    "frontend": ["react"],
    "web": ["react", "node.js"],
    # AI, ML & Deep Learning
    "deep learning": ["tensorflow", "keras"],
    "neural networks": ["tensorflow", "keras"],
    "machine learning": ["ml", "tensorflow"],
    "ai": ["ml", "tensorflow"],
    "nlp": ["ml", "python"],
    # Cloud & DevOps
    "cloud": ["aws", "azure"],
    "devops": ["aws", "azure", "node.js"],
    "docker": ["aws", "azure"],
    "kubernetes": ["aws", "azure"],
    "ci/cd": ["aws", "azure"],
    # Data & Analytics
    "data analytics": ["data science"],
    "data analysis": ["data science", "python"],
    "sql": ["data science", "python"],
}


class RecommendationEngine:
    def __init__(self, mongo_uri=MONGO_URI):
        self.mongo_uri = mongo_uri
        self.vectorizer = None
        self.label_encoder = None
        self.model = None
        self.jobs = []
        self.users = []
        self.classes = []
        self.job_vectors = None
        self.train()

    def get_db(self):
        client = pymongo.MongoClient(self.mongo_uri)
        return client, client['alumni_database']

    # ──────────────────────────────────────────────────────────────
    #  TRAINING  (Content-Based Model: TF-IDF + Multinomial NB)
    # ──────────────────────────────────────────────────────────────
    def train(self):
        client, db = self.get_db()
        try:
            self.jobs  = list(db['jobs'].find({}, {"_id": 0}))
            self.users = list(db['profiles'].find({}, {"_id": 0}))
        finally:
            client.close()

        # Fallback to JSON files if DB is empty
        if not self.jobs:
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

        job_texts  = []
        job_labels = []

        for job in self.jobs:
            skills = job.get("required_skills", "")
            desc   = job.get("description", "")
            if skills:
                job_texts.append(f"{skills} {desc}")
                job_labels.append(job.get("title", "Unknown"))

        if not job_texts:
            raise ValueError("No valid jobs available for training!")

        # TF-IDF vectorizer trained on job skill text
        self.vectorizer = TfidfVectorizer(stop_words="english", min_df=1, ngram_range=(1, 2))
        X_train = self.vectorizer.fit_transform(job_texts)

        # Store job vectors for cosine-similarity (content-based matching)
        self.job_vectors = X_train

        # Multinomial Naive Bayes classifier for role prediction
        self.label_encoder = LabelEncoder()
        y_train = self.label_encoder.fit_transform(job_labels)
        self.classes = list(self.label_encoder.classes_)

        self.model = MultinomialNB(alpha=1.0)
        self.model.fit(X_train, y_train)

    # ──────────────────────────────────────────────────────────────
    #  COLLABORATIVE FILTERING HELPERS
    # ──────────────────────────────────────────────────────────────
    def _get_collaborative_roles(self, skills_str: str, top_n: int = 3) -> list:
        if not self.users:
            return []

        candidate_skills = set(
            s.strip().lower() for s in skills_str.replace(',', ' ').split() if s.strip()
        )
        if not candidate_skills:
            return []

        role_scores: Counter = Counter()

        for user in self.users:
            user_skills = set(
                s.strip().lower()
                for s in (user.get("skills") or "").replace(',', ' ').split()
                if s.strip()
            )
            if not user_skills:
                continue
            intersection = candidate_skills & user_skills
            union        = candidate_skills | user_skills
            if not union:
                continue
            jaccard = len(intersection) / len(union)
            if jaccard > 0.1:
                role = user.get("recommended_role") or user.get("title") or user.get("desired_role")
                if role:
                    role_scores[role] += jaccard

        if not role_scores:
            return []

        total = sum(role_scores.values())
        return [(role, score / total) for role, score in role_scores.most_common(top_n)]

    def _get_collaborative_roles_from_notifications(self, skills_str: str, top_n: int = 3) -> list:
        client, db = self.get_db()
        try:
            notifications = list(db['notifications'].find({}, {"_id": 0, "user_name": 1, "job_title": 1}))
            profiles_map = {
                u.get("name"): u.get("skills", "")
                for u in self.users
            }
        finally:
            client.close()

        if not notifications:
            return []

        candidate_skills = set(
            s.strip().lower() for s in skills_str.replace(',', ' ').split() if s.strip()
        )
        if not candidate_skills:
            return []

        # Deduplicate to only the most recent recommendation per user
        latest_by_user = {}
        for notif in notifications:
            uname = notif.get("user_name")
            if uname and notif.get("job_title"):
                latest_by_user[uname] = notif.get("job_title")

        role_scores: Counter = Counter()

        for user_name, job_title in latest_by_user.items():
            user_skills_raw = profiles_map.get(user_name, "")
            if not user_skills_raw:
                continue
            user_skills = set(
                s.strip().lower()
                for s in user_skills_raw.replace(',', ' ').split() if s.strip()
            )
            if not user_skills:
                continue
            intersection = candidate_skills & user_skills
            union        = candidate_skills | user_skills
            if not union:
                continue
            jaccard = len(intersection) / len(union)
            if jaccard > 0.05:
                role_scores[job_title] += jaccard

        if not role_scores:
            return []

        total = sum(role_scores.values())
        return [(role, score / total) for role, score in role_scores.most_common(top_n)]

    # ──────────────────────────────────────────────────────────────
    #  MULTI-FACTOR HYBRID JOB RANKING (Content + Skills + Location + Role + Experience)
    # ──────────────────────────────────────────────────────────────
    def _rank_jobs(self, user_text: str, candidate_skills: set, candidate_location: str,
                   candidate_exp: int, hybrid_role_scores: dict):
        """
        Rank all jobs in database using multi-factor scoring.
        CRITICAL CONSTRAINT: A job MUST have at least 1 matching skill (direct or related)
        to receive a valid recommendation score. Zero skill matches receive score 0.0.
        """
        user_vec = self.vectorizer.transform([user_text])
        similarities = cosine_similarity(user_vec, self.job_vectors)[0]

        cand_loc_clean = (candidate_location or "").strip().lower()

        ranked = []
        for i, job in enumerate(self.jobs):
            job_exp = int(job.get("experience_required", 0) or 0)
            job_skills_raw = job.get("required_skills", "")
            job_skill_tokens = set(
                s.strip().lower() for s in job_skills_raw.replace(',', ' ').split() if s.strip()
            )

            # 1. Direct skill matches
            direct_matches = list(candidate_skills & job_skill_tokens)

            # 2. Semantic/ontology-related skill matches
            related_matches = []
            for c_skill in candidate_skills:
                for rel_key, mapped_skills in SKILL_RELATIONS.items():
                    if rel_key == c_skill or rel_key in c_skill:
                        for ms in mapped_skills:
                            if ms in job_skill_tokens and ms not in direct_matches and ms not in related_matches:
                                related_matches.append(ms)

            all_matched_skills = direct_matches + related_matches
            matched_count = len(all_matched_skills)
            skill_ratio   = matched_count / max(1, len(job_skill_tokens))
            is_qualified  = candidate_exp >= job_exp

            # Location match bonus
            job_loc_clean = (job.get("location") or "").strip().lower()
            loc_matched   = bool(cand_loc_clean and job_loc_clean == cand_loc_clean)
            loc_bonus     = 0.20 if loc_matched else 0.0

            csim       = float(similarities[i])
            role_score = float(hybrid_role_scores.get(job.get("title"), 0.0))

            # STRICT PREREQUISITE:
            # If zero skills match, the score is strictly 0.0 and job CANNOT be recommended.
            if matched_count == 0:
                score = 0.0
            else:
                score = (csim * 0.30) + (skill_ratio * 0.35) + (role_score * 0.15) + loc_bonus
                if not is_qualified:
                    score *= 0.6  # experience penalty

            ranked.append({
                "title":               job.get("title"),
                "company":             job.get("company"),
                "location":            job.get("location"),
                "description":         job.get("description"),
                "required_skills":     job_skills_raw,
                "experience_required": job_exp,
                "is_qualified":        is_qualified,
                "matched_skills":      all_matched_skills,
                "direct_matched":      direct_matches,
                "similarity_score":    round(score, 4),
                "location_matched":    loc_matched,
            })

        # Sort descending by composite similarity score
        ranked.sort(key=lambda x: x["similarity_score"], reverse=True)
        return ranked

    # ──────────────────────────────────────────────────────────────
    #  MAIN RECOMMEND METHOD (Hybrid: Content-Based + Collaborative + Location)
    # ──────────────────────────────────────────────────────────────
    def recommend(self, skills, bio="", experience=0, user_name="Guest User",
                  location="", save_notification=True):

        if isinstance(skills, list):
            skills_str = ", ".join(skills)
        else:
            skills_str = str(skills or "")

        bio_str  = str(bio or "").strip()
        user_exp = int(experience or 0)
        user_loc = str(location or "").strip()
        user_text = f"{skills_str} {bio_str}".strip()

        if not user_text:
            return {
                "success": False,
                "error": "Please provide skills or a bio for recommendation."
            }

        # ── Content-Based: NB classifier probabilities ──
        X_test = self.vectorizer.transform([user_text])
        probs  = self.model.predict_proba(X_test)[0]   # values in [0, 1]

        # Build probability dict {role: prob}
        prob_dict = {
            self.label_encoder.inverse_transform([i])[0]: float(p)
            for i, p in enumerate(probs)
        }

        # ── Collaborative: role signals from similar users' history ──
        collab_roles = self._get_collaborative_roles_from_notifications(skills_str)

        # ── Hybrid fusion: weighted combination ──
        CONTENT_W = 0.7
        COLLAB_W  = 0.3

        hybrid_scores = dict(prob_dict)

        for role, score in collab_roles:
            if role in hybrid_scores:
                hybrid_scores[role] = (CONTENT_W * hybrid_scores[role]) + (COLLAB_W * score)
            else:
                hybrid_scores[role] = COLLAB_W * score

        # Candidate skills token set
        user_skill_tokens = set(
            s.strip().lower() for s in skills_str.replace(',', ' ').split() if s.strip()
        )

        # ── Multi-factor job ranking across database (location-aware) ──
        all_ranked_jobs = self._rank_jobs(
            user_text=user_text,
            candidate_skills=user_skill_tokens,
            candidate_location=user_loc,
            candidate_exp=user_exp,
            hybrid_role_scores=hybrid_scores
        )

        # Sort role predictions for breakdown display
        sorted_roles = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
        top_predictions_list = [
            {"title": role, "confidence": round(score * 100, 1)}
            for role, score in sorted_roles[:5]
        ]
        probabilities_for_frontend = {
            row["title"]: row["confidence"] / 100.0
            for row in top_predictions_list
        }

        # ── STRICT SKILL CHECK: Only jobs with AT LEAST 1 matching skill can be recommended ──
        jobs_with_skills = [j for j in all_ranked_jobs if len(j["matched_skills"]) > 0 and j["similarity_score"] > 0]

        if not jobs_with_skills:
            # ZERO skills matched any position in the database!
            return {
                "success":                 True,
                "predicted_role":          "No Matching Role",
                "confidence":              0.0,
                "probabilities":           probabilities_for_frontend,
                "top_predictions":         top_predictions_list,
                "matched_job":             None,
                "all_role_matches":        [],
                "has_skill_match":         False,
                "has_experience_conflict": False,
                "constraint_message":      (
                    f"No open positions in our database match the entered skills ('{skills_str}'). "
                    "Current listings require technologies such as Python, React, Node.js, AWS, Azure, Java, Keras, Tensorflow, or Data Science."
                ),
                "notification_saved":      False,
            }

        qualified_jobs = [j for j in jobs_with_skills if j["is_qualified"]]
        best_match = qualified_jobs[0] if qualified_jobs else jobs_with_skills[0]

        # Predicted role aligns with the best match's title
        recommended_title = best_match["title"]

        # Best confidence (fraction, 0.0–1.0)
        best_conf_score = best_match["similarity_score"]
        best_confidence_frac = min(0.96, max(0.40, best_conf_score))

        # ── Persist notification with full candidate & job info (ONLY when skills match) ──
        notification_saved = False
        if best_match and save_notification:
            client, db = self.get_db()
            try:
                notification = {
                    "user_name":            user_name,
                    "job_title":            best_match["title"],
                    "company":              best_match["company"],
                    "location":             best_match["location"],
                    "description":          best_match["description"],
                    "experience_required":  best_match.get("experience_required", 0),
                    "required_skills":      best_match.get("required_skills", ""),
                    "similarity_score":     round(best_match.get("similarity_score", 0.0), 3),
                    "status":               "unread",
                    "candidate_skills":     skills_str,
                    "candidate_experience": user_exp,
                    "candidate_location":   user_loc,
                    "candidate_bio":        bio_str,
                }
                db.notifications.insert_one(notification)
                notification_saved = True
            except Exception as e:
                print("Could not save notification:", e)
            finally:
                client.close()

        has_exp_conflict = not best_match.get("is_qualified", True)
        constraint_msg = (
            f"You match the skills for {best_match['title']}, but your {user_exp} yr experience is below the required {best_match.get('experience_required', 0)} yr."
            if has_exp_conflict else ""
        )

        return {
            "success":                 True,
            "predicted_role":          recommended_title,
            "confidence":              round(best_confidence_frac, 4),
            "probabilities":           probabilities_for_frontend,
            "top_predictions":         top_predictions_list,
            "matched_job":             best_match,
            "all_role_matches":        jobs_with_skills[:10],
            "has_skill_match":         True,
            "has_experience_conflict": has_exp_conflict,
            "constraint_message":      constraint_msg,
            "notification_saved":      notification_saved,
        }

    # ──────────────────────────────────────────────────────────────
    #  BATCH (runs for all users in DB)
    # ──────────────────────────────────────────────────────────────
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
                location=user.get("location", ""),
                save_notification=True,
            )
            results.append({
                "user":             user.get("name"),
                "skills":           user.get("skills"),
                "experience":       user.get("experience"),
                "recommended_role": rec.get("predicted_role"),
                "confidence_pct":   round((rec.get("confidence") or 0) * 100, 1),
                "matched":          rec.get("matched_job") is not None,
            })
        return results
