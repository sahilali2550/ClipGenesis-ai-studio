"""
Smart Script Features - Multi-language translation, SEO optimization, script rephrasing, fact-checking, tone selection.
"""

import re
import json
from typing import Optional, List, Dict
from loguru import logger
from app.services import llm as llm_service
from app.config import config


class SmartScriptEngine:
    """Advanced script enhancement and analysis engine"""

    # Supported languages with codes
    SUPPORTED_LANGUAGES = {
        "en": "English", "es": "Spanish", "fr": "French", "de": "German",
        "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ja": "Japanese",
        "ko": "Korean", "zh": "Chinese", "ar": "Arabic", "hi": "Hindi",
        "tr": "Turkish", "pl": "Polish", "nl": "Dutch", "sv": "Swedish",
        "ur": "Urdu", "fa": "Persian", "id": "Indonesian", "th": "Thai",
        "vi": "Vietnamese"
    }

    # Tone presets
    TONE_PRESETS = {
        "neutral": {
            "name": "Neutral / Informative",
            "prompt_modifier": "Write in a neutral, informative tone. Factual and balanced."
        },
        "energetic": {
            "name": "Energetic / Excited",
            "prompt_modifier": "Write with high energy and enthusiasm. Use exclamation points and engaging language."
        },
        "professional": {
            "name": "Professional / Authoritative",
            "prompt_modifier": "Write in a professional, authoritative tone suitable for business or academic content."
        },
        "casual": {
            "name": "Casual / Conversational",
            "prompt_modifier": "Write in a casual, conversational tone as if talking to a friend."
        },
        "humorous": {
            "name": "Humorous / Witty",
            "prompt_modifier": "Write with humor and wit. Include light jokes and playful language."
        },
        "motivational": {
            "name": "Motivational / Inspiring",
            "prompt_modifier": "Write in a motivational and inspiring tone. Use power words and uplifting language."
        },
        "mysterious": {
            "name": "Mysterious / Curious",
            "prompt_modifier": "Write in a mysterious tone that builds curiosity and intrigue."
        },
        "educational": {
            "name": "Educational / Teacher-like",
            "prompt_modifier": "Write as a teacher explaining a concept. Clear, structured, with examples."
        },
    }

    def translate_script(self, script: str, target_language: str) -> str:
        """Translate script to target language"""
        if target_language == "en" or target_language == "auto":
            return script

        lang_name = self.SUPPORTED_LANGUAGES.get(target_language, target_language)
        prompt = f"""Translate the following video script to {lang_name}.
Keep the same tone and style.
Maintain proper punctuation for TTS (end sentences with periods, question marks, exclamation points).
Do NOT add any explanations or notes. Return ONLY the translated script.

Script:
{script}"""
        try:
            result = llm_service._generate_response(prompt)
            return result if result else script
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return script

    def optimize_seo(self, title: str, script: str) -> Dict:
        """Generate SEO-optimized title, description, and hashtags"""
        prompt = f"""Generate SEO-optimized metadata for this YouTube video.

Title: {title}
Script: {script[:500]}

Return ONLY a JSON object with this exact structure (no markdown, no extra text):
{{
  "optimized_title": "SEO-optimized title (max 60 chars)",
  "description": "2-3 line SEO description with keywords",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}"""
        try:
            result = llm_service._generate_response(prompt)
            # Parse JSON from response
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.error(f"SEO optimization failed: {e}")
        return self._default_seo(title, script)

    def rephrase_script(self, script: str, style: str = "clearer") -> str:
        """Rephrase script with different style"""
        modifiers = {
            "clearer": "Make this script clearer and easier to understand while keeping the same meaning.",
            "shorter": "Shorten this script by 30% while keeping all key points.",
            "engaging": "Make this script more engaging and hooky for viewers.",
            "formal": "Rewrite this script in a more formal, professional tone.",
            "casual": "Rewrite this script in a more casual, conversational tone.",
            "storytelling": "Rewrite this script as a compelling story with narrative flow.",
        }
        modifier = modifiers.get(style, modifiers["clearer"])
        prompt = f"""{modifier}

Original script:
{script}

Return ONLY the rephrased script. No explanations."""
        try:
            result = llm_service._generate_response(prompt)
            return result if result else script
        except Exception as e:
            logger.error(f"Script rephrase failed: {e}")
            return script

    def fact_check(self, script: str) -> Dict:
        """Basic fact-checking - identify potential claims that need verification"""
        prompt = f"""Analyze this video script for factual claims that might need verification.

Script:
{script}

Return ONLY a JSON object (no markdown):
{{
  "claims": [
    {{"claim": "exact quote from script", "category": "statistic|scientific|historical|general", "confidence": "high|medium|low"}}
  ],
  "warnings": ["any concerning claims that might be misleading"],
  "overall_reliability": "high|medium|low"
}}

If there are no specific claims, return: {{"claims": [], "warnings": [], "overall_reliability": "high"}}"""
        try:
            result = llm_service._generate_response(prompt)
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.error(f"Fact check failed: {e}")
        return {"claims": [], "warnings": [], "overall_reliability": "medium"}

    def apply_tone(self, script: str, tone: str) -> str:
        """Apply a specific tone to the script"""
        if tone not in self.TONE_PRESETS:
            return script

        preset = self.TONE_PRESETS[tone]
        prompt = f"""{preset['prompt_modifier']}

Original script:
{script}

Rewrite the script with this tone applied. Return ONLY the rewritten script."""
        try:
            result = llm_service._generate_response(prompt)
            return result if result else script
        except Exception as e:
            logger.error(f"Tone application failed: {e}")
            return script

    def analyze_readability(self, script: str) -> Dict:
        """Analyze script readability metrics"""
        sentences = re.split(r'[.!?]+', script)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = script.split()
        syllables = sum(self._count_syllables(w) for w in words)

        if not sentences or not words:
            return {"score": 0, "level": "unknown", "metrics": {}}

        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = syllables / len(words)
        flesch_score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word

        if flesch_score >= 80:
            level = "Very Easy"
        elif flesch_score >= 60:
            level = "Standard"
        elif flesch_score >= 40:
            level = "Moderate"
        elif flesch_score >= 20:
            level = "Difficult"
        else:
            level = "Very Difficult"

        return {
            "score": round(flesch_score, 1),
            "level": level,
            "metrics": {
                "word_count": len(words),
                "sentence_count": len(sentences),
                "avg_sentence_length": round(avg_sentence_length, 1),
                "avg_syllables_per_word": round(avg_syllables_per_word, 1),
            }
        }

    def generate_hooks(self, topic: str, count: int = 5) -> List[str]:
        """Generate attention-grabbing hooks for a topic"""
        prompt = f"""Generate {count} attention-grabbing hooks/opening lines for a video about: {topic}

Each hook should:
- Start with a question, surprising fact, or bold statement
- Be 1-2 sentences max
- Make viewers want to keep watching

Return ONLY a JSON array of strings (no markdown):
["hook 1", "hook 2", "hook 3", "hook 4", "hook 5"]"""
        try:
            result = llm_service._generate_response(prompt)
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.error(f"Hook generation failed: {e}")
        return []

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (approximate)"""
        word = word.lower()
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith("e"):
            count -= 1
        return max(count, 1)

    def _default_seo(self, title: str, script: str) -> Dict:
        words = script.split()[:100]
        return {
            "optimized_title": title[:60],
            "description": script[:200] + "...",
            "hashtags": ["#video", "#trending", "#viral"],
            "keywords": list(set(w.lower().strip('.,!?;:') for w in words))[:5]
        }


# Global instance
smart_script = SmartScriptEngine()
