import React from 'react';

const StudyPlanPage: React.FC = () => {
  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Study Plan</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">
            Personalized study plans based on your target date and progress.
          </p>
          <p className="text-sm text-gray-500 mt-4">
            This page will contain personalized study schedules and progress tracking.
          </p>
        </div>
      </div>
    </div>
  );
};

export default StudyPlanPage;
