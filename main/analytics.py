"""
RedIron Performance Lab - Analytics Module

Pure deterministic functions for calculating fitness performance metrics.
No external API calls - all rule-based scoring logic.
"""

from datetime import timedelta, datetime
from typing import Dict, List, Optional
from decimal import Decimal


class PerformanceAnalytics:
    """
    Production-grade analytics for fitness tracking.
    All calculations are deterministic and rule-based.
    """

    # ============================================
    # 1. ONE-REP MAX (1RM) CALCULATION
    # ============================================
    @staticmethod
    def calculate_1rm(weight: float, reps: int) -> float:
        """
        Calculate estimated One-Rep Max using Epley formula.
        
        Formula: 1RM = weight × (1 + reps/30)
        
        Args:
            weight: Weight lifted (kg)
            reps: Number of repetitions performed
            
        Returns:
            Estimated 1RM in kg
            
        Example:
            calculate_1rm(100, 10) → 133.33 kg
        """
        if weight <= 0 or reps <= 0:
            return 0.0
        
        # Epley formula
        one_rm = weight * (1 + reps / 30)
        return round(one_rm, 2)

    # ============================================
    # 2. STRENGTH SCORE
    # ============================================
    @staticmethod
    def calculate_strength_score(
        exercise_logs: List[Dict],
        body_weight: float = 80.0
    ) -> Dict[str, float]:
        """
        Calculate strength score based on relative strength (1RM / bodyweight).
        
        Scoring Scale:
        - Beginner: 0-1.0x bodyweight
        - Intermediate: 1.0-2.0x bodyweight
        - Advanced: 2.0-3.5x bodyweight
        - Elite: 3.5x+ bodyweight
        
        Args:
            exercise_logs: List of exercise log dicts with 'calculated_1rm' key
            body_weight: User's body weight in kg
            
        Returns:
            Dict with overall_score, level, and detailed breakdown
        """
        if not exercise_logs or body_weight <= 0:
            return {
                'overall_score': 0,
                'level': 'Beginner',
                'relative_strength': 0,
                'count': 0
            }

        # Calculate average relative strength (1RM / bodyweight)
        total_relative = sum(log.get('calculated_1rm', 0) for log in exercise_logs) / body_weight
        avg_relative = total_relative / len(exercise_logs) if exercise_logs else 0

        # Determine level
        if avg_relative < 1.0:
            level = 'Beginner'
            score = avg_relative * 25  # 0-25 points
        elif avg_relative < 2.0:
            level = 'Intermediate'
            score = 25 + (avg_relative - 1.0) * 25  # 25-50 points
        elif avg_relative < 3.5:
            level = 'Advanced'
            score = 50 + (avg_relative - 2.0) * (30 / 1.5)  # 50-80 points
        else:
            level = 'Elite'
            score = min(100, 80 + (avg_relative - 3.5) * 10)  # 80-100 points

        return {
            'overall_score': round(score, 1),
            'level': level,
            'relative_strength': round(avg_relative, 2),
            'count': len(exercise_logs)
        }

    # ============================================
    # 3. WEEKLY VOLUME CALCULATION
    # ============================================
    @staticmethod
    def calculate_weekly_volume(
        sessions: List[Dict],
        days_back: int = 7
    ) -> Dict[str, float]:
        """
        Calculate total training volume for the past N days.
        
        Volume = sum(weight × reps × sets) for all exercises
        
        Args:
            sessions: List of session dicts with 'total_volume' key
            days_back: Number of days to look back (default 7)
            
        Returns:
            Dict with total_volume, avg_per_session, and session_count
        """
        if not sessions:
            return {
                'total_volume': 0.0,
                'avg_per_session': 0.0,
                'session_count': 0,
                'period_days': days_back
            }

        total_volume = sum(session.get('total_volume', 0) for session in sessions)
        avg_per_session = total_volume / len(sessions) if sessions else 0

        return {
            'total_volume': round(total_volume, 2),
            'avg_per_session': round(avg_per_session, 2),
            'session_count': len(sessions),
            'period_days': days_back
        }

    # ============================================
    # 4. CALORIE BALANCE (TDEE vs Intake)
    # ============================================
    @staticmethod
    def calculate_calorie_balance(
        daily_intake: int,
        tdee: int = 2000,
        goal_type: str = 'muscle_gain'
    ) -> Dict[str, float]:
        """
        Calculate calorie balance for goal achievement.
        
        Rules:
        - Fat Loss: Target 300-500 cal deficit
        - Muscle Gain: Target 300-500 cal surplus
        - Maintenance: Close to 0
        
        Args:
            daily_intake: Calories consumed (kcal)
            tdee: Total Daily Energy Expenditure (kcal)
            goal_type: Goal type (fat_loss, muscle_gain, strength, endurance)
            
        Returns:
            Dict with balance, goal_status, and recommendation
        """
        balance = daily_intake - tdee

        goal_status = 'On Track'
        recommendation = 'Keep going!'

        if goal_type == 'fat_loss':
            optimal_min, optimal_max = -500, -300
            if balance > optimal_min:
                goal_status = 'Undereating'
                recommendation = 'Increase calories slightly to avoid muscle loss'
            elif balance < optimal_max:
                goal_status = 'Eating More Than Goal'
                recommendation = 'Stay consistent with deficit'
            else:
                goal_status = 'Optimal'
                recommendation = 'Perfect intake for fat loss'

        elif goal_type == 'muscle_gain':
            optimal_min, optimal_max = 300, 500
            if balance < optimal_min:
                goal_status = 'Undereating'
                recommendation = 'Eat more to support muscle growth'
            elif balance > optimal_max:
                goal_status = 'Overeating'
                recommendation = 'Slight excess is acceptable'
            else:
                goal_status = 'Optimal'
                recommendation = 'Perfect intake for muscle growth'

        else:  # maintenance / strength / endurance
            if abs(balance) < 100:
                goal_status = 'Optimal'
                recommendation = 'Maintenance intake is perfect'
            elif balance > 100:
                goal_status = 'Eating More'
                recommendation = 'Slight surplus is acceptable'
            else:
                goal_status = 'Slight Deficit'
                recommendation = 'Minor deficit is acceptable'

        return {
            'balance': round(balance, 1),
            'goal_status': goal_status,
            'recommendation': recommendation,
            'daily_intake': daily_intake,
            'tdee': tdee
        }

    # ============================================
    # 5. TRAINING STREAK
    # ============================================
    @staticmethod
    def calculate_streak(session_dates: List) -> Dict[str, int]:
        """
        Calculate current training streak (consecutive days with workouts).
        
        Args:
            session_dates: List of datetime objects when workouts occurred
            
        Returns:
            Dict with current_streak, longest_streak, and dates
        """
        if not session_dates:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'last_workout': None
            }

        # Sort dates
        sorted_dates = sorted(set(d.date() if hasattr(d, 'date') else d for d in session_dates))

        if not sorted_dates:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'last_workout': None
            }

        # Calculate streaks
        current_streak = 0
        longest_streak = 0
        temp_streak = 1

        for i in range(len(sorted_dates) - 1, -1, -1):
            if i == len(sorted_dates) - 1:
                temp_streak = 1
            else:
                days_diff = (sorted_dates[i + 1] - sorted_dates[i]).days
                if days_diff == 1:
                    temp_streak += 1
                else:
                    current_streak = temp_streak if i == len(sorted_dates) - 1 else 0
                    longest_streak = max(longest_streak, temp_streak)
                    temp_streak = 1

        # Handle last iteration
        if len(sorted_dates) > 0:
            last_date = sorted_dates[-1]
            today = datetime.now().date()
            if (today - last_date).days <= 1:
                current_streak = temp_streak
            else:
                current_streak = 0
            longest_streak = max(longest_streak, temp_streak)

        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'last_workout': sorted_dates[-1] if sorted_dates else None
        }

    # ============================================
    # 6. RECOMMENDATIONS (RULE-BASED)
    # ============================================
    @staticmethod
    def generate_recommendations(
        strength_score: Dict,
        weekly_volume: Dict,
        calorie_balance: Dict,
        body_metrics: Optional[Dict] = None
    ) -> List[Dict[str, str]]:
        """
        Generate rule-based recommendations based on performance metrics.
        
        Returns list of actionable recommendations with categories.
        """
        recommendations = []

        # Strength recommendations
        if strength_score['level'] == 'Beginner':
            recommendations.append({
                'type': 'Strength',
                'priority': 'high',
                'message': 'Focus on compound movements (Squat, Bench, Deadlift) to build foundational strength',
                'article_category': 'strength-training'
            })
        elif strength_score['level'] == 'Intermediate':
            recommendations.append({
                'type': 'Strength',
                'priority': 'medium',
                'message': 'Incorporate progressive overload by adding 2.5-5kg weekly to main lifts',
                'article_category': 'progressive-overload'
            })
        elif strength_score['level'] == 'Advanced':
            recommendations.append({
                'type': 'Strength',
                'priority': 'medium',
                'message': 'Consider periodized training with deload weeks every 3-4 weeks',
                'article_category': 'advanced-periodization'
            })

        # Volume recommendations
        if weekly_volume['session_count'] < 3:
            recommendations.append({
                'type': 'Frequency',
                'priority': 'high',
                'message': 'Aim for at least 3-4 training sessions per week for optimal progress',
                'article_category': 'training-frequency'
            })
        elif weekly_volume['session_count'] > 6:
            recommendations.append({
                'type': 'Recovery',
                'priority': 'high',
                'message': 'More than 6 sessions per week may lead to overtraining - ensure adequate recovery',
                'article_category': 'recovery-overtraining'
            })

        # Nutrition recommendations
        if calorie_balance['goal_status'] == 'Undereating':
            recommendations.append({
                'type': 'Nutrition',
                'priority': 'high',
                'message': f"Increase calorie intake to {calorie_balance['tdee'] + 350} kcal for your goal",
                'article_category': 'nutrition-calorie-surplus'
            })
        elif calorie_balance['goal_status'] == 'Optimal':
            recommendations.append({
                'type': 'Nutrition',
                'priority': 'low',
                'message': 'Your calorie intake aligns perfectly with your goal - maintain consistency',
                'article_category': 'nutrition-tracking'
            })

        # Body metrics recommendations
        if body_metrics and 'weight_trend' in body_metrics:
            if body_metrics['weight_trend'] == 'increasing' and calorie_balance['daily_intake'] > calorie_balance['tdee']:
                recommendations.append({
                    'type': 'Body Composition',
                    'priority': 'medium',
                    'message': 'Weight is trending up - ensure protein intake is adequate (0.8-1g per lb)',
                    'article_category': 'protein-nutrition'
                })

        # General hydration reminder
        recommendations.append({
            'type': 'Recovery',
            'priority': 'low',
            'message': 'Stay hydrated - aim for 3-4 liters of water daily according to your activity level',
            'article_category': 'hydration-recovery'
        })

        return recommendations

    # ============================================
    # 7. BODY METRICS TREND ANALYSIS
    # ============================================
    @staticmethod
    def analyze_body_metrics(
        metrics_history: List[Dict]
    ) -> Dict:
        """
        Analyze body composition trends over time.
        
        Args:
            metrics_history: List of body metric records with 'weight' and 'recorded_at'
            
        Returns:
            Dict with trend analysis
        """
        if not metrics_history or len(metrics_history) < 2:
            return {
                'current_weight': metrics_history[0]['weight'] if metrics_history else 0,
                'trend': 'insufficient_data',
                'weekly_change': 0,
                'monthly_change': 0
            }

        # Sort by date
        sorted_metrics = sorted(metrics_history, key=lambda x: x['recorded_at'])

        current_weight = sorted_metrics[-1]['weight']
        oldest_weight = sorted_metrics[0]['weight']

        # Calculate weekly trend (last 7 days)
        one_week_ago = datetime.now() - timedelta(days=7)
        weekly_metrics = [m for m in sorted_metrics if m['recorded_at'] >= one_week_ago]
        weekly_change = (current_weight - weekly_metrics[0]['weight']) if weekly_metrics else 0

        # Calculate monthly trend (last 30 days)
        one_month_ago = datetime.now() - timedelta(days=30)
        monthly_metrics = [m for m in sorted_metrics if m['recorded_at'] >= one_month_ago]
        monthly_change = (current_weight - monthly_metrics[0]['weight']) if monthly_metrics else 0

        # Determine trend
        if weekly_change > 0.5:
            trend = 'gaining'
        elif weekly_change < -0.5:
            trend = 'losing'
        else:
            trend = 'stable'

        return {
            'current_weight': round(current_weight, 1),
            'trend': trend,
            'weekly_change': round(weekly_change, 2),
            'monthly_change': round(monthly_change, 2),
            'total_change': round(current_weight - oldest_weight, 2),
            'recording_count': len(sorted_metrics)
        }

    # ============================================
    # 8. MACRO BALANCE ANALYSIS
    # ============================================
    @staticmethod
    def analyze_macro_balance(
        daily_nutrition: Dict
    ) -> Dict[str, float]:
        """
        Analyze macronutrient distribution (protein, carbs, fat percentages).
        
        Ideal ratios:
        - Protein: 25-35% of calories
        - Carbs: 45-65% of calories
        - Fat: 20-35% of calories
        """
        calories = daily_nutrition.get('calories', 1)
        if calories == 0:
            return {
                'protein_percent': 0,
                'carbs_percent': 0,
                'fat_percent': 0,
                'status': 'No data'
            }

        protein = daily_nutrition.get('protein', 0)
        carbs = daily_nutrition.get('carbs', 0)
        fat = daily_nutrition.get('fat', 0)

        # Calculate percentages (1g protein = 4 cal, 1g carbs = 4 cal, 1g fat = 9 cal)
        protein_cal = protein * 4
        carbs_cal = carbs * 4
        fat_cal = fat * 9

        protein_percent = (protein_cal / calories * 100) if calories > 0 else 0
        carbs_percent = (carbs_cal / calories * 100) if calories > 0 else 0
        fat_percent = (fat_cal / calories * 100) if calories > 0 else 0

        return {
            'protein_percent': round(protein_percent, 1),
            'carbs_percent': round(carbs_percent, 1),
            'fat_percent': round(fat_percent, 1),
            'status': 'balanced' if (25 <= protein_percent <= 35) else 'adjust_macros'
        }
