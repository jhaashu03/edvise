import React from 'react';

const ProgressPage: React.FC = () => {
  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Progress Analytics</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">
            Detailed analytics of your preparation progress and performance trends.
          </p>
          <p className="text-sm text-gray-500 mt-4">
            This page will contain charts, graphs, and detailed analytics.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ProgressPage;
