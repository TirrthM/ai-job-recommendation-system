import json
import pymongo
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
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
        """
        Find the top-N most common job roles held by similar users in the
        database, based on skill overlap (Jaccard similarity).
        Returns a list of (role_title, normalized_score) tuples.
        """
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
            # Jaccard similarity
            intersection = candidate_skills & user_skills
            union        = candidate_skills | user_skills
            if not union:
                continue
            jaccard = len(intersection) / len(union)
            if jaccard > 0.1:  # Only consider reasonably similar users
                # Pull the recommended/tagged role for this user from notifications
                # (use their historical match) or fall back to their profile title
                role = user.get("recommended_role") or user.get("title") or user.get("desired_role")
                if role:
                    role_scores[role] += jaccard

        if not role_scores:
            return []

        total = sum(role_scores.values())
        return [(role, score / total) for role, score in role_scores.most_common(top_n)]

    def _get_collaborative_roles_from_notifications(self, skills_str: str, top_n: int = 3) -> list:
        """
        Collaborative filtering using historical notification data:
        Find users with similar skills who were previously recommended certain roles.
        Deduplicates by user to avoid repetitive batch runs skewing the weights.
        """
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
        Rank all jobs in database using multi-factor scoring:
        1. TF-IDF cosine similarity between candidate skills/bio and job text
        2. Direct skill overlap ratio
        3. Role compatibility from hybrid classifier
        4. Location match bonus (+0.25) when candidate location matches job location
        5. Experience qualification
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
            common_skills = list(candidate_skills & job_skill_tokens)
            skill_ratio   = len(common_skills) / max(1, len(job_skill_tokens))
            is_qualified  = candidate_exp >= job_exp

            # Location match bonus
            job_loc_clean = (job.get("location") or "").strip().lower()
            loc_matched   = bool(cand_loc_clean and job_loc_clean == cand_loc_clean)
            loc_bonus     = 0.25 if loc_matched else 0.0

            csim       = float(similarities[i])
            role_score = float(hybrid_role_scores.get(job.get("title"), 0.0))

            # Composite match score: skill overlap + TF-IDF similarity + role prior + location bonus
            score = (csim * 0.35) + (skill_ratio * 0.25) + (role_score * 0.20) + loc_bonus
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
                "matched_skills":      common_skills,
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

        qualified_jobs = [j for j in all_ranked_jobs if j["is_qualified"]]
        best_match = qualified_jobs[0] if qualified_jobs else (all_ranked_jobs[0] if all_ranked_jobs else None)

        # Align predicted role with the best-matching job title
        if best_match:
            recommended_title = best_match["title"]
        else:
            sorted_roles = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
            recommended_title = sorted_roles[0][0] if sorted_roles else "Unknown"

        # Sort role predictions for breakdown display
        sorted_roles = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
        top_predictions_list = [
            {"title": role, "confidence": round(score * 100, 1)}
            for role, score in sorted_roles[:5]
        ]

        # Best confidence (fraction, 0.0–1.0)
        best_conf_score = best_match["similarity_score"] if best_match else sorted_roles[0][1]
        best_confidence_frac = min(0.96, max(0.45, best_conf_score))

        # ── Persist notification with full candidate & job info ──
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
                    # Store candidate details for modal display (even if not in DB)
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

        # Probabilities dict for the frontend (fraction 0.0–1.0)
        probabilities_for_frontend = {
            row["title"]: row["confidence"] / 100.0
            for row in top_predictions_list
        }

        return {
            "success":              True,
            "predicted_role":       recommended_title,
            "confidence":           round(best_confidence_frac, 4),
            "probabilities":        probabilities_for_frontend,
            "top_predictions":      top_predictions_list,
            "matched_job":          best_match,
            "all_role_matches":     all_ranked_jobs[:10],
            "has_experience_conflict": len(all_ranked_jobs) > 0 and len(qualified_jobs) == 0,
            "constraint_message":   (
                f"No jobs found where your {user_exp} yr experience meets the minimum requirement."
                if (len(all_ranked_jobs) > 0 and len(qualified_jobs) == 0) else ""
            ),
            "notification_saved":   notification_saved,
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
