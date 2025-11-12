/**
 * Skill Checklist Component
 * Shows student progress on course skills
 */

'use client';

import React, { useState, useEffect } from 'react';
import { learningService, SkillChecklist as SkillChecklistType, Skill } from '../../services/learningService';

interface SkillChecklistProps {
  studentId: string;
  courseId: string;
}

type FilterType = 'all' | 'not_started' | 'learning' | 'reviewing' | 'mastered';

export const SkillChecklist: React.FC<SkillChecklistProps> = ({
  studentId,
  courseId,
}) => {
  const [checklist, setChecklist] = useState<SkillChecklistType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>('all');
  const [expandedSkills, setExpandedSkills] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchChecklist = async () => {
      try {
        setIsLoading(true);
        const data = await learningService.getSkillChecklist(studentId, courseId);
        setChecklist(data);
        setIsLoading(false);
      } catch (err: any) {
        setError(err.message || 'Failed to load skill checklist');
        setIsLoading(false);
      }
    };

    fetchChecklist();
  }, [studentId, courseId]);

  const toggleSkillExpand = (skillId: string) => {
    const newExpanded = new Set(expandedSkills);
    if (newExpanded.has(skillId)) {
      newExpanded.delete(skillId);
    } else {
      newExpanded.add(skillId);
    }
    setExpandedSkills(newExpanded);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading skill checklist...</p>
        </div>
      </div>
    );
  }

  if (error || !checklist) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-red-800 font-semibold mb-2">Error</h3>
        <p className="text-red-600">{error || 'Failed to load checklist'}</p>
      </div>
    );
  }

  // Filter skills
  const filteredSkills = checklist.skills.filter((skill) => {
    if (filter === 'all') return true;
    return skill.status === filter;
  });

  // Group by topic
  const skillsByTopic: Record<string, Skill[]> = {};
  filteredSkills.forEach((skill) => {
    if (!skillsByTopic[skill.topic]) {
      skillsByTopic[skill.topic] = [];
    }
    skillsByTopic[skill.topic].push(skill);
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'mastered':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'reviewing':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'learning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'foundational':
        return 'text-green-600';
      case 'intermediate':
        return 'text-yellow-600';
      case 'advanced':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="space-y-6">
      {/* Overview */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
          Course Progress
        </h2>

        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Overall Mastery</span>
            <span>{checklist.overall_progress.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className="bg-blue-600 h-4 rounded-full transition-all"
              style={{ width: `${checklist.overall_progress}%` }}
            ></div>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-2xl font-bold text-gray-600">
              {checklist.total_skills}
            </p>
            <p className="text-xs text-gray-600">Total</p>
          </div>
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <p className="text-2xl font-bold text-green-600">
              {checklist.skills_mastered}
            </p>
            <p className="text-xs text-gray-600">Mastered</p>
          </div>
          <div className="text-center p-3 bg-yellow-50 rounded-lg">
            <p className="text-2xl font-bold text-yellow-600">
              {checklist.skills_in_progress}
            </p>
            <p className="text-xs text-gray-600">In Progress</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-2xl font-bold text-gray-400">
              {checklist.skills_not_started}
            </p>
            <p className="text-xs text-gray-600">Not Started</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {[
          { value: 'all' as FilterType, label: 'All Skills', count: checklist.total_skills },
          { value: 'mastered' as FilterType, label: 'Mastered', count: checklist.skills_mastered },
          { value: 'reviewing' as FilterType, label: 'Reviewing', count: Math.floor(checklist.skills_in_progress / 2) },
          { value: 'learning' as FilterType, label: 'Learning', count: Math.ceil(checklist.skills_in_progress / 2) },
          { value: 'not_started' as FilterType, label: 'Not Started', count: checklist.skills_not_started },
        ].map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              filter === f.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {f.label} ({f.count})
          </button>
        ))}
      </div>

      {/* Skills grouped by topic */}
      {Object.keys(skillsByTopic).length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
          <p className="text-gray-600">No skills match the current filter.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(skillsByTopic).map(([topic, skills]) => (
            <div key={topic} className="bg-white rounded-lg border border-gray-200">
              <div className="p-4 bg-gray-50 border-b border-gray-200">
                <h3 className="text-lg font-bold text-gray-800">{topic}</h3>
                <p className="text-sm text-gray-600">
                  {skills.length} skill{skills.length !== 1 ? 's' : ''}
                </p>
              </div>

              <div className="divide-y divide-gray-200">
                {skills.map((skill) => (
                  <div key={skill.skill_id} className="p-4">
                    <div
                      className="flex items-start justify-between cursor-pointer"
                      onClick={() => toggleSkillExpand(skill.skill_id)}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-semibold text-gray-800">
                            {skill.name}
                          </h4>
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(
                              skill.status
                            )}`}
                          >
                            {skill.status.replace('_', ' ')}
                          </span>
                          <span
                            className={`text-xs font-medium ${getDifficultyColor(
                              skill.difficulty
                            )}`}
                          >
                            {skill.difficulty}
                          </span>
                        </div>

                        <p className="text-sm text-gray-600 mb-2">
                          {skill.description}
                        </p>

                        {/* Progress bar */}
                        <div className="mb-2">
                          <div className="flex justify-between text-xs text-gray-600 mb-1">
                            <span>Mastery Level</span>
                            <span>{skill.mastery_level.toFixed(0)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                skill.mastery_level >= 90
                                  ? 'bg-green-600'
                                  : skill.mastery_level >= 60
                                  ? 'bg-yellow-600'
                                  : 'bg-blue-600'
                              }`}
                              style={{ width: `${skill.mastery_level}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>

                      <button className="ml-4 text-gray-400 hover:text-gray-600">
                        {expandedSkills.has(skill.skill_id) ? '▼' : '▶'}
                      </button>
                    </div>

                    {/* Expanded details */}
                    {expandedSkills.has(skill.skill_id) && (
                      <div className="mt-4 pt-4 border-t border-gray-200 space-y-3">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          <div>
                            <p className="text-xs text-gray-600">Practice</p>
                            <p className="font-semibold text-gray-800">
                              {skill.practice_attempts} attempts
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-600">Accuracy</p>
                            <p
                              className={`font-semibold ${
                                skill.accuracy_rate >= 80
                                  ? 'text-green-600'
                                  : skill.accuracy_rate >= 60
                                  ? 'text-yellow-600'
                                  : 'text-red-600'
                              }`}
                            >
                              {skill.accuracy_rate.toFixed(0)}%
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-600">Time Spent</p>
                            <p className="font-semibold text-gray-800">
                              {Math.floor(skill.time_spent_minutes / 60)}h{' '}
                              {skill.time_spent_minutes % 60}m
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-600">Est. Hours</p>
                            <p className="font-semibold text-gray-800">
                              {skill.estimated_hours}h
                            </p>
                          </div>
                        </div>

                        {skill.prerequisites.length > 0 && (
                          <div>
                            <p className="text-xs text-gray-600 mb-1">
                              Prerequisites:
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {skill.prerequisites.map((prereqId) => {
                                const prereq = checklist.skills.find(
                                  (s) => s.skill_id === prereqId
                                );
                                return prereq ? (
                                  <span
                                    key={prereqId}
                                    className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                                  >
                                    {prereq.name}
                                  </span>
                                ) : null;
                              })}
                            </div>
                          </div>
                        )}

                        {skill.last_practiced && (
                          <div>
                            <p className="text-xs text-gray-600">
                              Last practiced:{' '}
                              {new Date(skill.last_practiced).toLocaleDateString()}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SkillChecklist;
