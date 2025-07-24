import React from 'react';

const SyllabusPage: React.FC = () => {
  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">UPSC Syllabus</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">
            Comprehensive UPSC syllabus with detailed topics and subtopics.
          </p>
          <p className="text-sm text-gray-500 mt-4">
            This page will contain the full UPSC syllabus organized by papers and subjects.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SyllabusPage;
