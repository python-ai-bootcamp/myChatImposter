import React from 'react';

const BooleanField = ({ name, value, onChange }) => {
  return (
    <input
      type="checkbox"
      id={name}
      checked={!!value}
      onChange={(e) => onChange(e.target.checked)}
    />
  );
};

export default BooleanField;
