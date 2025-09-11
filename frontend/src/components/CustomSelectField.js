import React from 'react';
import { connectField } from 'uniforms';

const Select = ({ allowedValues, enumNames, label, onChange, value }) => {
  const options = allowedValues.map((val, index) => ({
    value: val,
    label: enumNames[index] || val,
  }));

  return (
    <div>
      <label>{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
      >
        {options.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export default connectField(Select);
