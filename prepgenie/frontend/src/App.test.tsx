import React from 'react';
import { render } from '@testing-library/react';

test('renders without crashing', () => {
  const div = document.createElement('div');
  const component = <div>PrepGenie Test</div>;
  render(component, { container: div });
  expect(div.textContent).toContain('PrepGenie Test');
});
