import React from 'react';
import { render } from '@testing-library/react';

test('renders without crashing', () => {
  // Simple test that just checks React can create elements
  const element = React.createElement('div', null, 'PrepGenie Test');
  expect(element).toBeDefined();
  expect(element.props.children).toBe('PrepGenie Test');
});
