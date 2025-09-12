import React from 'react';

const StringField = ({ name, value, onChange, schema }) => {
  if (schema.enum) {
    return (
      <select
        id={name}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: '4px' }}
      >
        {schema.enum.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  return (
    <input
      type="text"
      id={name}
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: '4px' }}
    />
  );
};

export default StringField;
