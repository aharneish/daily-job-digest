#!/usr/bin/env python3
"""
Quick debug script to see what's happening with your LinkedIn jobs
Run this to understand why jobs are being filtered out
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Test configuration
REQUIRED_SKILLS = os.getenv("REQUIRED_SKILLS", "").split(",") if os.getenv("REQUIRED_SKILLS") else []
PREFERRED_SKILLS = os.getenv("PREFERRED_SKILLS", "python,tensorflow,pytorch,scikit-learn,machine learning,deep learning,AI,artificial intelligence").split(",")
EXCLUDE_KEYWORDS = os.getenv("EXCLUDE_KEYWORDS", "").split(",") if os.getenv("EXCLUDE_KEYWORDS") else []
MIN_SKILL_MATCH_SCORE = int(os.getenv("MIN_SKILL_MATCH_SCORE", "1"))

# Clean up skills (remove whitespace)
REQUIRED_SKILLS = [skill.strip().lower() for skill in REQUIRED_SKILLS if skill.strip()]
PREFERRED_SKILLS = [skill.strip().lower() for skill in PREFERRED_SKILLS if skill.strip()]
EXCLUDE_KEYWORDS = [kw.strip().lower() for kw in EXCLUDE_KEYWORDS if kw.strip()]

print("🔧 DEBUG: Current Filter Configuration")
print(f"   • Required Skills: {REQUIRED_SKILLS}")
print(f"   • Preferred Skills: {PREFERRED_SKILLS[:10]}... (showing first 10)")
print(f"   • Exclude Keywords: {EXCLUDE_KEYWORDS}")
print(f"   • Min Skill Score: {MIN_SKILL_MATCH_SCORE}")

def test_job_text(job_title, job_description=""):
    """Test a sample job against our filters"""
    print(f"\n📋 Testing Job: {job_title}")
    
    job_text = f"{job_title} {job_description}".lower()
    print(f"📝 Full job text: {job_text}")
    
    # Test required skills
    if REQUIRED_SKILLS:
        missing_required = []
        for skill in REQUIRED_SKILLS:
            if skill not in job_text:
                missing_required.append(skill)
        
        if missing_required:
            print(f"❌ Missing required skills: {missing_required}")
        else:
            print(f"✅ All required skills found")
    
    # Test excluded keywords
    found_excluded = []
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in job_text:
            found_excluded.append(keyword)
    
    if found_excluded:
        print(f"❌ Found excluded keywords: {found_excluded}")
    else:
        print(f"✅ No excluded keywords found")
    
    # Test preferred skills
    found_skills = []
    for skill in PREFERRED_SKILLS:
        if skill in job_text:
            found_skills.append(skill)
    
    skill_score = len(found_skills)
    print(f"⭐ Skill score: {skill_score} (found: {found_skills})")
    
    if skill_score < MIN_SKILL_MATCH_SCORE:
        print(f"❌ Skill score too low ({skill_score} < {MIN_SKILL_MATCH_SCORE})")
    else:
        print(f"✅ Skill score meets requirement")
    
    # Overall result
    passes_filter = (
        (not REQUIRED_SKILLS or not missing_required) and
        not found_excluded and
        skill_score >= MIN_SKILL_MATCH_SCORE
    )
    
    print(f"🎯 RESULT: {'PASSES FILTER' if passes_filter else 'FILTERED OUT'}")
    return passes_filter

# Test with sample job titles that might come from LinkedIn
print("\n" + "="*60)
print("🧪 TESTING SAMPLE ML JOB TITLES")
print("="*60)

sample_jobs = [
    "Machine Learning Engineer",
    "Senior Machine Learning Engineer", 
    "ML Engineer - Python/TensorFlow",
    "Data Scientist - Machine Learning",
    "AI/ML Engineer",
    "Machine Learning Developer",
    "Junior Machine Learning Engineer",  # This should be filtered out
    "ML Engineer Intern",  # This should be filtered out
]

passed_jobs = 0
for job_title in sample_jobs:
    passed = test_job_text(job_title)
    if passed:
        passed_jobs += 1

print(f"\n📊 SUMMARY: {passed_jobs}/{len(sample_jobs)} sample jobs passed filters")

if passed_jobs == 0:
    print("\n🚨 ISSUE FOUND: No jobs are passing your filters!")
    print("💡 SUGGESTIONS:")
    print("   1. Remove required skills or make them less restrictive")
    print("   2. Lower MIN_SKILL_MATCH_SCORE to 1")
    print("   3. Check if exclude keywords are too broad")
    print("   4. Verify your .env file has the right format")

print("\n🔍 Next step: Run your main script with the debug methods I provided above!")