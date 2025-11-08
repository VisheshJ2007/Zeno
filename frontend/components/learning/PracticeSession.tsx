/**
 * Practice Session Component
 * Interactive spaced repetition practice session with FSRS
 */

'use client';

import React, { useState, useEffect } from 'react';
import { learningService, SessionCard } from '../../services/learningService';

interface PracticeSessionProps {
  studentId: string;
  courseId: string;
  sessionType?: 'daily_review' | 'topic_focused' | 'exam_prep' | 'mixed';
  topics?: string[];
  onComplete?: (summary: any) => void;
}

export const PracticeSession: React.FC<PracticeSessionProps> = ({
  studentId,
  courseId,
  sessionType = 'daily_review',
  topics,
  onComplete,
}) => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [cards, setCards] = useState<SessionCard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startTime, setStartTime] = useState<number>(Date.now());
  const [sessionSummary, setSessionSummary] = useState<any>(null);

  // Initialize session
  useEffect(() => {
    const initSession = async () => {
      try {
        setIsLoading(true);
        const response = await learningService.createSession({
          student_id: studentId,
          course_id: courseId,
          session_type: sessionType,
          target_card_count: 20,
          topics: topics,
          interleaved: true,
        });

        setSessionId(response.session_id);
        setCards(response.cards);
        setIsLoading(false);
      } catch (err: any) {
        setError(err.message || 'Failed to create practice session');
        setIsLoading(false);
      }
    };

    initSession();
  }, [studentId, courseId, sessionType, topics]);

  const handleRating = async (rating: 1 | 2 | 3 | 4) => {
    if (!sessionId) return;

    const timeSpent = Math.floor((Date.now() - startTime) / 1000);
    const currentCard = cards[currentIndex];

    try {
      // Submit response
      const response = await learningService.submitCardResponse(
        sessionId,
        studentId,
        {
          card_id: currentCard.card_id,
          rating,
          time_spent_seconds: timeSpent,
        }
      );

      // Check if session is complete
      if (response.is_complete) {
        const summary = await learningService.completeSession(
          sessionId,
          studentId
        );
        setSessionSummary(summary);
        if (onComplete) {
          onComplete(summary);
        }
      } else {
        // Move to next card
        setCurrentIndex(currentIndex + 1);
        setShowAnswer(false);
        setStartTime(Date.now());
      }
    } catch (err: any) {
      setError(err.message || 'Failed to submit response');
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading practice session...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-red-800 font-semibold mb-2">Error</h3>
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  // No cards available
  if (cards.length === 0) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
        <p className="text-blue-800 font-semibold mb-2">No cards due for review</p>
        <p className="text-blue-600">Great job! You're all caught up!</p>
      </div>
    );
  }

  // Session complete
  if (sessionSummary) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-green-800 mb-4">
          Session Complete! 🎉
        </h2>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg">
            <p className="text-gray-600 text-sm">Cards Completed</p>
            <p className="text-2xl font-bold text-gray-800">
              {sessionSummary.cards_completed}
            </p>
          </div>

          <div className="bg-white p-4 rounded-lg">
            <p className="text-gray-600 text-sm">Accuracy</p>
            <p className="text-2xl font-bold text-green-600">
              {sessionSummary.accuracy_rate}%
            </p>
          </div>

          <div className="bg-white p-4 rounded-lg">
            <p className="text-gray-600 text-sm">Time Spent</p>
            <p className="text-2xl font-bold text-gray-800">
              {Math.floor(sessionSummary.total_time_seconds / 60)}m
            </p>
          </div>

          <div className="bg-white p-4 rounded-lg">
            <p className="text-gray-600 text-sm">Avg per Card</p>
            <p className="text-2xl font-bold text-gray-800">
              {sessionSummary.average_time_per_card}s
            </p>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg mb-4">
          <h3 className="font-semibold text-gray-800 mb-2">Rating Distribution</h3>
          <div className="flex gap-2">
            {Object.entries(sessionSummary.rating_distribution).map(
              ([rating, count]) => (
                <div key={rating} className="flex-1 text-center">
                  <div className="text-xs text-gray-600 mb-1">
                    {
                      { '1': 'Again', '2': 'Hard', '3': 'Good', '4': 'Easy' }[
                        rating
                      ]
                    }
                  </div>
                  <div className="text-lg font-bold">{count}</div>
                </div>
              )
            )}
          </div>
        </div>

        <button
          onClick={() => window.location.reload()}
          className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition"
        >
          Start New Session
        </button>
      </div>
    );
  }

  // Active session - show current card
  const currentCard = cards[currentIndex];
  const progress = ((currentIndex + 1) / cards.length) * 100;

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>
            Card {currentIndex + 1} of {cards.length}
          </span>
          <span>{Math.round(progress)}% complete</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      {/* Card */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-md p-8 mb-6">
        {/* Topic and difficulty badges */}
        <div className="flex gap-2 mb-4">
          <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
            {currentCard.topic}
          </span>
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              currentCard.difficulty === 'easy'
                ? 'bg-green-100 text-green-800'
                : currentCard.difficulty === 'medium'
                ? 'bg-yellow-100 text-yellow-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {currentCard.difficulty}
          </span>
        </div>

        {/* Question */}
        <div className="mb-6">
          <h3 className="text-xl font-semibold text-gray-800 mb-4">
            {currentCard.question.question_text}
          </h3>

          {/* Multiple choice options */}
          {currentCard.question.question_type === 'multiple_choice' &&
            currentCard.question.options && (
              <div className="space-y-2">
                {currentCard.question.options.map((option, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                  >
                    {option}
                  </div>
                ))}
              </div>
            )}
        </div>

        {/* Show answer button */}
        {!showAnswer && (
          <button
            onClick={() => setShowAnswer(true)}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
          >
            Show Answer
          </button>
        )}

        {/* Answer and rating buttons */}
        {showAnswer && (
          <div className="space-y-4">
            {currentCard.question.hint && (
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm font-semibold text-yellow-800 mb-1">
                  Hint
                </p>
                <p className="text-yellow-700">{currentCard.question.hint}</p>
              </div>
            )}

            <div className="text-center">
              <p className="text-sm text-gray-600 mb-3">
                How well did you know this?
              </p>
              <div className="grid grid-cols-4 gap-2">
                <button
                  onClick={() => handleRating(1)}
                  className="py-3 bg-red-100 text-red-800 rounded-lg font-semibold hover:bg-red-200 transition"
                >
                  Again
                  <span className="block text-xs font-normal">Forgot</span>
                </button>
                <button
                  onClick={() => handleRating(2)}
                  className="py-3 bg-orange-100 text-orange-800 rounded-lg font-semibold hover:bg-orange-200 transition"
                >
                  Hard
                  <span className="block text-xs font-normal">Difficult</span>
                </button>
                <button
                  onClick={() => handleRating(3)}
                  className="py-3 bg-green-100 text-green-800 rounded-lg font-semibold hover:bg-green-200 transition"
                >
                  Good
                  <span className="block text-xs font-normal">Correct</span>
                </button>
                <button
                  onClick={() => handleRating(4)}
                  className="py-3 bg-blue-100 text-blue-800 rounded-lg font-semibold hover:bg-blue-200 transition"
                >
                  Easy
                  <span className="block text-xs font-normal">Very easy</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Help text */}
      <div className="text-center text-sm text-gray-500">
        <p>
          Rate your answer based on how well you knew it. This helps optimize
          your review schedule.
        </p>
      </div>
    </div>
  );
};

export default PracticeSession;
