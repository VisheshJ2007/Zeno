/**
 * Analytics Dashboard Component
 * Shows topic accuracy trends and student performance metrics
 */

'use client';

import React, { useState, useEffect } from 'react';
import { learningService, StudentAnalytics, TopicAnalytics } from '../../services/learningService';

interface AnalyticsDashboardProps {
  studentId: string;
  courseId: string;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  studentId,
  courseId,
}) => {
  const [analytics, setAnalytics] = useState<StudentAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setIsLoading(true);
        const data = await learningService.getStudentAnalytics(studentId, courseId);
        setAnalytics(data);
        setIsLoading(false);
      } catch (err: any) {
        setError(err.message || 'Failed to load analytics');
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, [studentId, courseId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error || !analytics) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-red-800 font-semibold mb-2">Error</h3>
        <p className="text-red-600">{error || 'Failed to load analytics'}</p>
      </div>
    );
  }

  const selectedTopicData = selectedTopic
    ? analytics.topic_analytics.find((t) => t.topic === selectedTopic)
    : null;

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-gray-600 text-sm mb-1">Overall Accuracy</p>
          <p className="text-3xl font-bold text-blue-600">
            {analytics.overall_accuracy.toFixed(1)}%
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-gray-600 text-sm mb-1">Cards Reviewed</p>
          <p className="text-3xl font-bold text-gray-800">
            {analytics.total_cards_reviewed}
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-gray-600 text-sm mb-1">Current Streak</p>
          <p className="text-3xl font-bold text-green-600">
            {analytics.current_streak_days}
            <span className="text-lg ml-1">days</span>
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-gray-600 text-sm mb-1">Due Today</p>
          <p className="text-3xl font-bold text-orange-600">
            {analytics.cards_due_today}
          </p>
        </div>
      </div>

      {/* Skill Mastery */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-xl font-bold text-gray-800 mb-4">Skill Mastery</h2>
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Overall Progress</span>
            <span>{analytics.overall_mastery.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className="bg-blue-600 h-4 rounded-full transition-all duration-300"
              style={{ width: `${analytics.overall_mastery}%` }}
            ></div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <p className="text-2xl font-bold text-green-600">
              {analytics.skills_mastered}
            </p>
            <p className="text-sm text-gray-600">Mastered</p>
          </div>
          <div className="text-center p-3 bg-yellow-50 rounded-lg">
            <p className="text-2xl font-bold text-yellow-600">
              {analytics.skills_in_progress}
            </p>
            <p className="text-sm text-gray-600">In Progress</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-2xl font-bold text-gray-600">
              {analytics.skills_not_started}
            </p>
            <p className="text-sm text-gray-600">Not Started</p>
          </div>
        </div>
      </div>

      {/* Accuracy Trends */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-xl font-bold text-gray-800 mb-4">
          Accuracy Trend (30 days)
        </h2>
        <div className="h-40 flex items-end justify-between gap-1">
          {analytics.accuracy_trend_30d.map((accuracy, idx) => (
            <div key={idx} className="flex-1 flex flex-col items-center">
              <div
                className="w-full bg-blue-600 rounded-t transition-all hover:bg-blue-700"
                style={{ height: `${accuracy}%` }}
                title={`${accuracy.toFixed(1)}%`}
              ></div>
            </div>
          ))}
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-2">
          <span>30 days ago</span>
          <span>Today</span>
        </div>
      </div>

      {/* Topic Analytics */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-xl font-bold text-gray-800 mb-4">
          Topic Performance
        </h2>

        {analytics.topic_analytics.length === 0 ? (
          <p className="text-gray-600">No topic data available yet.</p>
        ) : (
          <div className="space-y-4">
            {analytics.topic_analytics.map((topic) => (
              <div
                key={topic.topic}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition cursor-pointer"
                onClick={() =>
                  setSelectedTopic(
                    selectedTopic === topic.topic ? null : topic.topic
                  )
                }
              >
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-semibold text-gray-800">{topic.topic}</h3>
                  <span className="text-sm text-gray-600">
                    {topic.total_attempts} attempts
                  </span>
                </div>

                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-gray-600">Overall Accuracy</span>
                  <span
                    className={`text-lg font-bold ${
                      topic.overall_accuracy >= 80
                        ? 'text-green-600'
                        : topic.overall_accuracy >= 60
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}
                  >
                    {topic.overall_accuracy.toFixed(1)}%
                  </span>
                </div>

                {/* Accuracy by difficulty */}
                <div className="grid grid-cols-3 gap-2 mb-2">
                  <div className="text-center p-2 bg-green-50 rounded">
                    <p className="text-xs text-gray-600">Easy</p>
                    <p className="font-bold text-green-600">
                      {topic.accuracy_by_difficulty.easy.toFixed(0)}%
                    </p>
                  </div>
                  <div className="text-center p-2 bg-yellow-50 rounded">
                    <p className="text-xs text-gray-600">Medium</p>
                    <p className="font-bold text-yellow-600">
                      {topic.accuracy_by_difficulty.medium.toFixed(0)}%
                    </p>
                  </div>
                  <div className="text-center p-2 bg-red-50 rounded">
                    <p className="text-xs text-gray-600">Hard</p>
                    <p className="font-bold text-red-600">
                      {topic.accuracy_by_difficulty.hard.toFixed(0)}%
                    </p>
                  </div>
                </div>

                {/* Expanded view with trend */}
                {selectedTopic === topic.topic && topic.accuracy_trend.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <h4 className="font-semibold text-gray-700 mb-3">
                      Accuracy Trend Over Time
                    </h4>
                    <div className="space-y-2">
                      {topic.accuracy_trend.map((point, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between text-sm"
                        >
                          <span className="text-gray-600 w-24">{point.date}</span>
                          <div className="flex-1 mx-4">
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${
                                  point.accuracy_rate >= 80
                                    ? 'bg-green-600'
                                    : point.accuracy_rate >= 60
                                    ? 'bg-yellow-600'
                                    : 'bg-red-600'
                                }`}
                                style={{ width: `${point.accuracy_rate}%` }}
                              ></div>
                            </div>
                          </div>
                          <span className="font-medium w-16 text-right">
                            {point.accuracy_rate.toFixed(1)}%
                          </span>
                          <span className="text-gray-500 text-xs w-20 text-right">
                            ({point.attempts} cards)
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recommendations */}
      {(analytics.recommended_topics.length > 0 ||
        analytics.recommended_skills.length > 0) && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h2 className="text-xl font-bold text-yellow-900 mb-4">
            Recommendations
          </h2>

          {analytics.recommended_topics.length > 0 && (
            <div className="mb-4">
              <h3 className="font-semibold text-yellow-800 mb-2">
                Topics Needing Attention
              </h3>
              <div className="flex flex-wrap gap-2">
                {analytics.recommended_topics.map((topic) => (
                  <span
                    key={topic}
                    className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analytics.recommended_skills.length > 0 && (
            <div>
              <h3 className="font-semibold text-yellow-800 mb-2">
                Ready to Learn
              </h3>
              <div className="flex flex-wrap gap-2">
                {analytics.recommended_skills.map((skill) => (
                  <span
                    key={skill}
                    className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Study Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-gray-600 text-sm mb-1">Time Invested</p>
          <p className="text-2xl font-bold text-gray-800">
            {Math.floor(analytics.total_time_minutes / 60)}h{' '}
            {analytics.total_time_minutes % 60}m
          </p>
        </div>

        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <p className="text-gray-600 text-sm mb-1">Active Days</p>
          <p className="text-2xl font-bold text-gray-800">
            {analytics.active_days}
          </p>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
