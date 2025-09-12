import React from 'react';

const NumberField = ({ name, value, onChange }) => {
  const handleChange = (e) => {
    const val = e.target.value;
    // If the input is empty, pass the empty string so AJV can catch the type error.
    // Otherwise, convert to a number.
    onChange(val === '' ? val : Number(val));
  };

  return (
    <input
      type="number"
      id={name}
      value={value === undefined || value === null ? '' : value}
      onChange={handleChange}
      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: '4px' }}
    />
  );
};

export default NumberField;
